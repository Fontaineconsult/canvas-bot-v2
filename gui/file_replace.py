"""GUI-side file replace orchestration.

Pure helpers (no UI) used by the Content Viewer's single Replace flow and
the upcoming bulk replace feature. UI flows (dialogs, threading, progress
widgets) will land in this module in subsequent steps.
"""

import json
import logging
import os
import threading
import time
import warnings
from tkinter import filedialog

import customtkinter as ctk

from gui.network import replace_file_with_progress
from gui.widgets import _add_focus_ring, show_dialog

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


_STAGE_LABELS = {
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

    file_path = filedialog.askopenfilename(
        title="Select replacement file",
        initialdir=initial_dir,
    )
    if not file_path:
        return

    original_title = row.get("title", "file")
    original_ext = os.path.splitext(original_title)[1].lower()
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

    def _on_done(result):
        progress.close()
        if cancel_event.is_set():
            log.info(f"File replace cancelled by user: {original_title}")
            return
        if result:
            new_name = result.get("display_name", result.get("filename", os.path.basename(file_path)))
            viewer._apply_replaced_to_ui(canvas_file_id)
            show_dialog(parent, "File Replaced",
                        f"Successfully replaced '{original_title}' with '{new_name}'.",
                        dialog_type="info")
        else:
            show_dialog(parent, "Replace Failed",
                        f"Failed to replace '{original_title}'. Check the log for details.",
                        dialog_type="error")

    # Throttle state — touched only from the worker thread (single writer).
    throttle = {"last_emit": 0.0, "last_stage": None}

    def _on_progress(stage, bytes_read, total):
        now = time.monotonic()
        # Always emit on stage change or on completion; otherwise gate on interval.
        if (stage != throttle["last_stage"]
                or stage in ("done",)
                or now - throttle["last_emit"] >= _PROGRESS_THROTTLE_SEC):
            throttle["last_emit"] = now
            throttle["last_stage"] = stage
            parent.after(0, progress.update_progress, stage, bytes_read, total)

    def _worker():
        try:
            result = perform_replace(
                course_id, canvas_file_id, file_path,
                on_progress=_on_progress,
                cancel_event=cancel_event,
            )
        except Exception:
            log.exception("Unhandled error in replace worker")
            result = None
        parent.after(0, _on_done, result)

    threading.Thread(target=_worker, daemon=True, name="canvas-replace").start()
