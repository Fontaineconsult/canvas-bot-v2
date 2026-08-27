import logging
import yaml
import os
import re
import sys
import shutil

from core.platform_compat import hide_directory, user_config_dir

log = logging.getLogger(__name__)


def _get_bundled_path(filename):
    """
    Get path to a bundled resource file.
    Works both in development and when compiled with PyInstaller.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled exe - use PyInstaller's temp directory
        base_path = os.path.join(sys._MEIPASS, 'config')
    else:
        # Running as script - use source directory
        base_path = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(base_path, filename)


def _get_user_re_path():
    """
    Get path to the user-editable re.yaml in the platform config directory.
    Creates the file from bundled default if it doesn't exist.

    On Windows this is %APPDATA%/canvas bot, unchanged from previous versions.
    """
    app_folder = user_config_dir()
    user_re_path = os.path.join(app_folder, "re.yaml")

    # Create app folder if needed
    if not os.path.exists(app_folder):
        os.makedirs(app_folder, exist_ok=True)

    # Copy bundled default to user location if it doesn't exist
    if not os.path.exists(user_re_path):
        bundled_path = _get_bundled_path("re.yaml")
        if os.path.exists(bundled_path):
            shutil.copy(bundled_path, user_re_path)

    return user_re_path


def _substitute_placeholders(data, env_vars=None):
    """
    Recursively substitute {PLACEHOLDER} patterns with environment variable values.
    If env_vars dict is provided, use it; otherwise fall back to os.environ.
    """
    if env_vars is None:
        env_vars = os.environ

    if isinstance(data, str):
        # Find all {PLACEHOLDER} patterns and replace with env values
        def replace_match(match):
            key = match.group(1)
            return env_vars.get(key, match.group(0))  # Keep original if not found
        return re.sub(r'\{([A-Z_]+)\}', replace_match, data)
    elif isinstance(data, list):
        return [_substitute_placeholders(item, env_vars) for item in data]
    elif isinstance(data, dict):
        return {k: _substitute_placeholders(v, env_vars) for k, v in data.items()}
    else:
        return data


def read_config(substitute=False):
    config_path = _get_bundled_path("config.yaml")
    with open(config_path, "r", encoding='utf_8') as f:
        data = yaml.safe_load(f)
    if substitute:
        return _substitute_placeholders(data)
    return data


def read_re(substitute=True):
    """
    Read regex patterns from re.yaml.
    Uses user-editable copy in AppData (auto-created from bundled default if needed).
    By default, substitutes {PLACEHOLDER} patterns with environment variable values.

    The user's copy is created once from the bundled default and never updated, so
    a copy made by an older version can be missing keys that newer code expects
    (e.g. ``canvas_file_scope_regex``). That would raise KeyError at import in
    sorters.sorters and prevent the app from starting. To stay resilient to such
    schema additions, any top-level key present in the bundled default but missing
    from the user's file is backfilled here (in memory only — we never overwrite
    the user's file, preserving their edits/formatting).
    """
    re_path = _get_user_re_path()
    with open(re_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    bundled_path = _get_bundled_path("re.yaml")
    if os.path.exists(bundled_path):
        try:
            with open(bundled_path, "r", encoding="utf-8") as f:
                defaults = yaml.safe_load(f) or {}
            for key, value in defaults.items():
                if key not in data:
                    log.warning("re.yaml missing key %r; using bundled default", key)
                    data[key] = value
        except Exception as exc:  # never let backfill itself break loading
            log.warning("Could not merge bundled re.yaml defaults: %s", exc)

    if substitute:
        return _substitute_placeholders(data)
    return data


def write_re(data):
    """Write patterns back to user's re.yaml in AppData."""
    path = _get_user_re_path()
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def reset_re():
    """Reset user's re.yaml to bundled default by deleting the user copy."""
    # Built directly rather than via _get_user_re_path(), which would recreate
    # the file from the bundled default just so we could delete it again.
    user_re_path = os.path.join(user_config_dir(), "re.yaml")
    if os.path.exists(user_re_path):
        os.remove(user_re_path)
        return True
    return False

def read_download_manifest(course_folder):
    try:
        with open(os.path.join(course_folder, ".manifest", "download_manifest.yaml"), "r+") as f:
            return yaml.safe_load(f)
    except FileNotFoundError as exc:
        log.error(f"Failed to read download manifest file: {course_folder} | {exc}")
        raise SystemExit(f"Download manifest file not found: {course_folder}")


def write_to_download_manifest(course_folder: str, heading:str, content_list: list):
    yaml_content = {"downloaded_files": content_list}

    with open(os.path.join(course_folder, ".manifest", "download_manifest.yaml"),"w") as f:
        yaml.dump(yaml_content, f, default_flow_style=False, allow_unicode=True)

def create_download_manifest(course_folder: str) -> str:

    manifest_dir = os.path.join(course_folder, ".manifest")

    if not os.path.exists(manifest_dir):
        try:
            os.makedirs(manifest_dir, exist_ok=True)
        except FileNotFoundError as exc:
            print("Could not create download manifest folder. Please check the course folder path and try again.")
            log.warning(f"Failed to create download manifest folder: {course_folder} | {exc}")

    raw_manifest_path = _get_bundled_path("download_manifest.yaml")
    if not os.path.exists(os.path.join(manifest_dir, "download_manifest.yaml")):
        try:
            shutil.copy(raw_manifest_path, os.path.join(manifest_dir, "download_manifest.yaml"))

            hide_directory(manifest_dir)
        except FileNotFoundError as exc:
            print("Could not create download manifest file. Please check the course folder path and try again.")
            log.warning(f"Failed to create download manifest file: {course_folder} | {exc}")

    return manifest_dir

