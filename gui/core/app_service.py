"""Framework-agnostic application service for the Canvas Bot GUI.

This is the reusable seam between any GUI front-end and the Canvas engine. It
contains the logic the old CustomTkinter ``GUIController`` mixed with widget
code — credential checks, token validation, and the scan/download worker — but
with **zero GUI imports**. Callers pass plain callbacks for status/log updates
and marshal those onto their own UI thread (``wx.CallAfter``, ``root.after``,
etc.).

Everything here calls into already framework-agnostic engine code:
``canvas_bot.CanvasBot``, ``network.cred``, ``gui.validation``,
``sorters.sorters``, ``config.yaml_io``.
"""

import logging
import os
import subprocess
import sys
import threading

log = logging.getLogger(__name__)


def get_config_status():
    """Return (ok, message) describing whether Canvas Bot is configured.

    Thin wrapper over ``network.cred.check_config_status`` so GUIs don't import
    network internals directly.
    """
    from network.cred import check_config_status
    return check_config_status()


def validate_token_async(on_result):
    """Validate the stored API token on a daemon thread.

    Calls ``on_result(ok, message, info)`` from the worker thread when done;
    the caller is responsible for marshalling that onto its UI thread. ``info``
    is a dict (name/id/locale/api_path) on success, else None.
    """
    def _worker():
        try:
            from network.cred import validate_api_token
            ok, message, info = validate_api_token()
        except Exception as exc:  # pragma: no cover - defensive
            log.warning(f"Token validation crashed: {exc}")
            ok, message, info = False, f"{type(exc).__name__}: {exc}", None
        on_result(ok, message, info)

    threading.Thread(target=_worker, daemon=True, name="cb-token-validate").start()


def log_file_path():
    """Absolute path to the rotating log file under %APPDATA%/canvas bot/."""
    return os.path.join(os.environ.get("APPDATA", ""), "canvas bot", "canvas_bot.log")


def open_log_file():
    """Open the log file in the default editor. Returns (ok, message)."""
    try:
        path = log_file_path()
        if os.path.exists(path):
            os.startfile(path)  # noqa: S606 - intended desktop action, Windows-only
            return True, "Opened log file"
        return False, "No log file found"
    except Exception as exc:
        log.error(f"Failed to open log: {exc}")
        return False, f"Error: {exc}"


def launch_cli(flag):
    """Launch the CLI with a flag in a new console window. Returns (ok, message).

    Honors the frozen-exe vs. script distinction exactly as the old controller
    did, so ``--config_status`` / ``--reset_canvas_params`` open a real console.
    """
    try:
        creation = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        if getattr(sys, "frozen", False):
            subprocess.Popen([sys.executable, flag], creationflags=creation)
        else:
            subprocess.Popen([sys.executable, "canvas_bot.py", flag], creationflags=creation)
        return True, f"Launched {flag}"
    except Exception as exc:
        log.error(f"Failed to launch CLI: {exc}")
        return False, f"Error launching: {exc}"


def build_scan_params(options):
    """Translate the GUI options dict into the engine's **params kwargs.

    ``options`` uses the GUI/settings key names (include_video, ...); the engine
    expects its own names (include_video_files, only_active_files, ...). Mirrors
    the param dict the old controller built at controller.py:482-489.
    """
    return {
        "include_video_files": bool(options.get("include_video")),
        "include_audio_files": bool(options.get("include_audio")),
        "include_image_files": bool(options.get("include_image")),
        "download_hidden_files": bool(options.get("include_hidden")),
        "only_active_files": not bool(options.get("include_inactive")),
        "flatten": bool(options.get("flatten")),
    }


def resolve_course_ids(course_id, course_list_path):
    """Resolve the effective course-id list from the two input fields.

    Returns (course_ids, messages) where messages is a list of (level, text)
    tuples — level is "error" or "warning". A single course id is validated;
    a list path is read and filtered. Empty result with an error message means
    the caller should abort.
    """
    from canvas_bot import read_course_list
    from gui.validation import validate_course_id, validate_course_list

    messages = []
    course_id = (course_id or "").strip()
    course_list_path = (course_list_path or "").strip()

    if course_id:
        error = validate_course_id(course_id)
        if error:
            return [], [("error", error)]
        return [course_id], messages

    if course_list_path:
        raw_ids = read_course_list(course_list_path)
        valid, warnings = validate_course_list(raw_ids)
        for w in warnings:
            messages.append(("warning", w))
        if not valid:
            messages.append(("error", "No valid course IDs to process."))
        return valid, messages

    return [], [("error", "Enter a course ID or choose a course list file.")]


def run_scan(course_ids, options, on_status):
    """Run the scan/download for each course id. Blocking — call on a worker.

    This is the body of the old ``_run_worker`` (controller.py:431-540) with all
    tkinter coupling removed:
      - credentials are loaded and the API token set,
      - patterns reloaded,
      - each course is scanned (CanvasBot.start), its content.json written to
        ``.manifest/``, optional trees printed, and files downloaded.

    ``on_status(text)`` is called with short human-readable status strings; the
    caller marshals them to the UI. ``print()`` output flows to whatever
    stdout/stderr the caller has redirected. Returns (ok, summary_message).

    COM is initialized/uninitialized here because the download path touches
    Windows shell APIs (shortcut creation) from this worker thread.
    """
    pythoncom = None
    try:
        try:
            import pythoncom as _pythoncom
            pythoncom = _pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pythoncom = None

        from canvas_bot import CanvasBot
        from network.cred import (
            set_canvas_api_key_to_environment_variable,
            load_config_data_from_appdata,
        )

        if not load_config_data_from_appdata():
            on_status("Error - Not Configured")
            print("ERROR: Canvas Bot is not configured.")
            print("Click 'Reset Config' to configure your Canvas instance.")
            return False, "Not configured"

        from sorters.sorters import reload_patterns
        reload_patterns()

        if not set_canvas_api_key_to_environment_variable():
            on_status("Error - No API Token")
            print("ERROR: No Canvas API access token found.")
            print("Click 'Reset Config' to set up your API token.")
            return False, "No API token"

        params = build_scan_params(options)
        output_folder = (options.get("output_folder") or "").strip() or None
        do_download = bool(options.get("download"))
        do_content_tree = bool(options.get("content_tree"))
        do_full_tree = bool(options.get("full_tree"))

        total = len(course_ids)
        for i, course_id in enumerate(course_ids, 1):
            on_status(f"Processing course {i}/{total} (ID: {course_id})...")
            print(f"\n{'=' * 50}")
            print(f"Course {i}/{total} — ID: {course_id}")
            print(f"{'=' * 50}\n")

            bot = CanvasBot(course_id)
            bot.start()

            course_folder = None
            if output_folder and bot.exists:
                from tools.string_checking.url_cleaning import sanitize_windows_filename
                course_folder = os.path.join(
                    os.path.normpath(output_folder),
                    f"{sanitize_windows_filename(bot.course_name)} - {bot.course_id}",
                )

            if course_folder:
                from config.yaml_io import create_download_manifest
                manifest_dir = create_download_manifest(course_folder)
                bot.save_content_as_json(manifest_dir, course_folder, **params)

            if do_content_tree:
                bot.print_content_tree()
            if do_full_tree:
                bot.print_full_course()

            if output_folder and do_download:
                bot.download_files(output_folder, **params)

        on_status("Complete")
        print(f"\nAll done — {total} course(s) processed.")
        return True, f"{total} course(s) processed"

    except Exception as exc:
        import traceback
        log.exception(f"Unhandled error: {type(exc).__name__}: {exc}")
        on_status("Error")
        traceback.print_exc()
        return False, f"{type(exc).__name__}: {exc}"

    finally:
        if pythoncom is not None:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
