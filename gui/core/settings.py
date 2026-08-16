"""Framework-agnostic GUI settings persistence.

Reads/writes the same ``gui_settings.json`` (in ``%APPDATA%/canvas bot/``) that
the original CustomTkinter controller used, but as a plain dict — no tkinter
StringVars. Both GUIs can share the file, so switching between ``--gui wx`` and
``--gui tk`` preserves the user's last inputs.
"""

import json
import os


# Default values for every persisted field. The wx Run panel reads/writes these
# keys; load() fills missing keys from here so older settings files still work.
DEFAULTS = {
    "course_id": "",
    "course_list": "",
    "output_folder": "",
    "download": True,
    "include_video": False,
    "include_audio": False,
    "include_image": False,
    "include_hidden": False,
    "include_inactive": False,
    "flatten": False,
    "content_tree": False,
    "full_tree": False,
}


def settings_path():
    """Absolute path to gui_settings.json under %APPDATA%/canvas bot/."""
    appdata = os.environ.get("APPDATA", "")
    return os.path.join(appdata, "canvas bot", "gui_settings.json")


def _read_raw():
    """Return the raw settings dict on disk, or {} when missing/corrupt."""
    try:
        with open(settings_path(), "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def load():
    """Load settings as a dict, filling defaults for any missing key.

    Mirrors the original controller's migration: if ``output_folder`` is empty,
    fall back to the legacy ``download_folder``/``excel_folder``/``json_folder``
    keys so users upgrading from an old build keep their folder.
    """
    data = _read_raw()
    result = dict(DEFAULTS)
    for key in DEFAULTS:
        if key in data:
            result[key] = data[key]

    if not result["output_folder"]:
        result["output_folder"] = (
            data.get("download_folder", "")
            or data.get("excel_folder", "")
            or data.get("json_folder", "")
        )
    return result


def save(values):
    """Persist the given settings dict, preserving unrelated keys on disk.

    Only the keys present in ``values`` (plus whatever was already stored, such
    as ``first_run``) are written, so saving the Run-tab fields never clobbers
    the first-run flag.
    """
    data = _read_raw()
    data.update({k: values[k] for k in DEFAULTS if k in values})
    try:
        folder = os.path.dirname(settings_path())
        os.makedirs(folder, exist_ok=True)
        with open(settings_path(), "w") as f:
            json.dump(data, f, indent=4)
    except OSError:
        pass


def is_first_run():
    """True when the welcome dialog has not yet been dismissed."""
    return _read_raw().get("first_run", True)


def set_first_run_complete():
    """Record that the welcome dialog has been shown."""
    data = _read_raw()
    data["first_run"] = False
    try:
        folder = os.path.dirname(settings_path())
        os.makedirs(folder, exist_ok=True)
        with open(settings_path(), "w") as f:
            json.dump(data, f, indent=4)
    except OSError:
        pass
