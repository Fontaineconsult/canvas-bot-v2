"""File-upload primitives for Canvas's 3-step upload protocol.

  1. notify_file_upload  — POST /courses/:cid/files; returns (upload_url, upload_params).
  2. upload_file_bytes   — multipart-stream the bytes to upload_url; returns either the
                           final file dict (Canvas short-circuits) or a confirm_url.
  3. confirm_file_upload — GET confirm_url to finalize; returns the final file dict.

Orchestration (call all three, validate extensions, emit stages, honor cancel) lives
in core/replace.py:FileReplace.
"""

import json
import logging
import os
import warnings

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

from network.api import _clean_url, _extract_error_message
from network.cred import get_access_token

log = logging.getLogger(__name__)


def notify_file_upload(course_id, name, size, parent_folder_id, on_duplicate="overwrite"):
    """Step 1. Returns (upload_url, upload_params dict) on success, None on failure."""
    url = (f"{os.environ.get('API_PATH')}/courses/{course_id}"
           f"/files?access_token={get_access_token()}")
    clean = _clean_url(url)
    try:
        resp = requests.post(url, data={
            "name": name,
            "size": size,
            "parent_folder_id": parent_folder_id,
            "on_duplicate": on_duplicate,
        }, verify=True, timeout=(10, 30))
    except RequestsConnectionError as exc:
        log.error(f"Connection error during notify: {exc} | {clean}")
        return None

    if resp.status_code != 200:
        log.warning(f"Notify failed: {clean} | {resp.status_code}")
        try:
            err = _extract_error_message(json.loads(resp.content))
        except json.JSONDecodeError:
            err = resp.text
        warnings.warn(f"Notify failed: HTTP {resp.status_code} - {err}", UserWarning)
        return None

    info = json.loads(resp.content)
    upload_url = info.get("upload_url")
    upload_params = info.get("upload_params", {})
    if not upload_url:
        log.error("Notify returned no upload_url")
        return None
    log.info(f"Notify OK: {clean}")
    return upload_url, upload_params


def upload_file_bytes(upload_url, upload_params, local_path, original_name, on_bytes=None):
    """Step 2. Streams local_path to upload_url. on_bytes(bytes_read, total) is fired
    per socket write.

    Returns:
      - dict (final file metadata) when Canvas short-circuits (200/201 with 'id').
      - str (confirm_url) when Canvas wants a separate confirm step (3xx redirect, or
        200/201 with 'location').
      - None on failure.
    """
    try:
        with open(local_path, "rb") as fh:
            fields = dict(upload_params)
            fields["file"] = (original_name, fh, "application/octet-stream")
            encoder = MultipartEncoder(fields=fields)

            def _monitor(monitor):
                if on_bytes:
                    try:
                        on_bytes(monitor.bytes_read, monitor.len)
                    except Exception:
                        pass  # never let a callback bug kill the upload

            monitor = MultipartEncoderMonitor(encoder, _monitor)

            resp = requests.post(
                upload_url,
                data=monitor,
                headers={"Content-Type": monitor.content_type},
                verify=True,
                allow_redirects=False,
                timeout=(10, 600),
            )
    except (RequestsConnectionError, OSError) as exc:
        log.error(f"Connection error during upload: {exc}")
        return None

    if resp.status_code in (301, 302, 303):
        return resp.headers.get("Location")
    if resp.status_code in (200, 201):
        try:
            result = json.loads(resp.content)
            if result.get("id"):
                log.info("Upload complete (no confirm needed)")
                return result
            return result.get("location")
        except json.JSONDecodeError:
            return None

    log.warning(f"Upload failed: {resp.status_code}")
    try:
        err = _extract_error_message(json.loads(resp.content))
    except json.JSONDecodeError:
        err = resp.text
    warnings.warn(f"Upload failed: HTTP {resp.status_code} - {err}", UserWarning)
    return None


def confirm_file_upload(confirm_url):
    """Step 3. Returns the final file dict on success, None on failure."""
    try:
        sep = "&" if "?" in confirm_url else "?"
        resp = requests.get(
            f"{confirm_url}{sep}access_token={get_access_token()}",
            verify=True,
            timeout=(10, 30),
        )
    except RequestsConnectionError as exc:
        log.error(f"Connection error during confirm: {exc}")
        return None

    if resp.status_code in (200, 201):
        log.info("Confirm OK")
        try:
            return json.loads(resp.content)
        except json.JSONDecodeError:
            return {"status": "ok"}

    log.warning(f"Confirm failed: {resp.status_code}")
    try:
        err = _extract_error_message(json.loads(resp.content))
    except json.JSONDecodeError:
        err = resp.text
    warnings.warn(f"Confirm failed: HTTP {resp.status_code} - {err}", UserWarning)
    return None