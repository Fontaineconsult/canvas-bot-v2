"""Replace — scaffold for rewriting file_id references in Canvas content.

Minimal: takes a course id and a page id, fetches and stores the page
body, prints it on demand. Will grow into a base class for per-source
subclasses (Page, Discussion, …) as we build out the rewriter.
"""

import os
import re
import warnings

from network.api import get_file, get_page, update_page
from network.files import notify_file_upload, upload_file_bytes, confirm_file_upload
from network.cred import set_canvas_api_key_to_environment_variable, load_config_data_from_appdata


_FILE_REF_RE = re.compile(r"/files/(\d+)\b")



class UpdateBody:
    def __init__(self, course_id, page_id):
        self.course_id = course_id
        self.page_id = page_id
        self.body = self._fetch_body()

    def _fetch_body(self):
        page = get_page(self.course_id, self.page_id)
        return page.get("body") if page else None


    def print_body(self):
        print(self.body)

    def rewrite(self, mapping):
        """Return a new body string with old file_ids swapped for new ones.

        `mapping` is a dict of `{old_file_id: new_file_id}`. IDs not in the
        mapping are left alone. Does not mutate self.body.
        """
        if not self.body:
            return ""

        def _swap(match):
            old = int(match.group(1))
            return f"/files/{mapping.get(old, old)}"

        return _FILE_REF_RE.sub(_swap, self.body)

    def push(self, new_body):
        """PUT new_body to the remote page. Returns True on success."""
        return bool(update_page(self.course_id, self.page_id, new_body))



class FileReplace:
    """Replace a Canvas file's contents with a new local file.

    Construct with (course_id, old_file_id, local_path), call run(), and on
    success self.new_file_id holds the id of the newly-uploaded attachment.
    Use that to build the {old_id: new_id} mapping for rewriting link
    references in pages.

    Optional callbacks:
      on_progress(stage, bytes_read, total) — stage is one of
        'fetching', 'notifying', 'uploading', 'confirming', 'done'.
        bytes_read and total are only meaningful during 'uploading'.
      cancel_event — threading.Event checked between stages (NOT mid-upload;
        a cancel during the upload is honored at the next stage boundary).
    """

    def __init__(self, course_id, old_file_id, local_path,
                 on_progress=None, cancel_event=None):
        self.course_id = course_id
        self.old_file_id = old_file_id
        self.local_path = local_path
        self.on_progress = on_progress
        self.cancel_event = cancel_event
        self.new_file_id = None

    def run(self):
        """Run the 3-step Canvas upload. Returns True on success; sets self.new_file_id."""
        if self._cancelled():
            return False

        # Step 0: existing file metadata.
        self._emit("fetching")
        existing = get_file(self.course_id, self.old_file_id)
        if not existing:
            warnings.warn(
                f"File replace failed: could not retrieve file {self.old_file_id}",
                UserWarning,
            )
            return False

        folder_id = existing.get("folder_id")
        original_name = existing.get("display_name") or existing.get("filename")
        if not folder_id or not original_name:
            warnings.warn("File replace failed: missing folder_id or filename", UserWarning)
            return False

        if not self._extensions_match(original_name):
            return False

        if self._cancelled():
            return False

        # Step 1: notify.
        self._emit("notifying")
        notify_result = notify_file_upload(
            self.course_id, original_name, os.path.getsize(self.local_path), folder_id,
        )
        if notify_result is None:
            return False
        upload_url, upload_params = notify_result

        if self._cancelled():
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
            return False

        # Branch: Canvas may short-circuit (dict) or hand back a confirm_url (str).
        if isinstance(upload_result, dict):
            file_dict = upload_result
        else:
            if self._cancelled():
                return False
            self._emit("confirming", filesize, filesize)
            file_dict = confirm_file_upload(upload_result)
            if file_dict is None:
                return False

        if not file_dict.get("id"):
            return False

        self.new_file_id = file_dict["id"]
        self._emit("done", filesize, filesize)
        return True

    def _extensions_match(self, original_name):
        original_ext = os.path.splitext(original_name)[1].lower()
        local_ext = os.path.splitext(self.local_path)[1].lower()
        if original_ext != local_ext:
            warnings.warn(
                f"File type mismatch: Canvas file is '{original_ext}' "
                f"but replacement is '{local_ext}'",
                UserWarning,
            )
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



if __name__=="__main__":
    set_canvas_api_key_to_environment_variable()
    load_config_data_from_appdata()


    def show(stage, b, t):
        print(f"  {stage}: {b}/{t}" if stage == "uploading" else f"  {stage}")
    fr = FileReplace("21016", 9175311, r"C:\Users\Fonta\Downloads\accessibility+-+jamovi.pdf", on_progress=show)
    fr.run()
    print(fr.new_file_id)