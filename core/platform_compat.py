r"""
Platform Compatibility Module
=============================

Centralizes the OS-specific behaviour Canvas Bot relies on, so the rest of the
codebase can stay platform-neutral.

Why This Exists
---------------
Canvas Bot was written Windows-first: it called ``ctypes.windll`` directly and
read ``%APPDATA%`` to locate its config. Neither works when the scan engine
runs headless on a Linux server, which is where the web UI executes it.

Rather than scatter ``if sys.platform == "win32"`` through the call sites,
callers express *intent* ("give me the config directory", "hide this
directory") and this module decides what that means for the host OS.

Not everything platform-specific lives here. Long-path (``\\?\``) handling
stays inline in ``core.downloader`` and ``core.content_extractor``, where it
was already correctly guarded by ``os.name == 'nt'`` before the port.

Design Rules
------------
1. Never raise because of the host platform. Degrade to a no-op instead.
2. On Windows, behave exactly as the pre-port code did — existing installs
   must keep finding their config in the same place.
3. Keep the surface small. Add a helper when a second call site needs it,
   not in anticipation of one.

See Also
--------
- config.yaml_io : Reads/writes config and the per-course download manifest
- tools.vba_to_excel : Uses IS_WINDOWS to gate Excel COM automation
"""

from __future__ import annotations

import logging
import os
import sys

import platformdirs

log = logging.getLogger(__name__)

APP_NAME = "canvas bot"

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

# FILE_ATTRIBUTE_HIDDEN
_FILE_ATTRIBUTE_HIDDEN = 0x02


def user_config_dir() -> str:
    """
    Absolute path to the user-editable config directory.

    On Windows this resolves to ``%APPDATA%\\canvas bot`` — byte-identical to
    the path the pre-port code built by hand, so existing installs keep their
    ``re.yaml`` and ``gui_settings.json``.

    Returns
    -------
    str
        Platform-appropriate config directory. Always absolute. Not created.

        =========  ==========================================
        Platform   Location
        =========  ==========================================
        Windows    ``%APPDATA%\\canvas bot``
        macOS      ``~/Library/Application Support/canvas bot``
        Linux      ``~/.config/canvas bot`` (respects XDG)
        =========  ==========================================
    """
    return platformdirs.user_config_dir(APP_NAME, appauthor=False, roaming=True)


def hide_directory(path: str) -> bool:
    """
    Mark a directory hidden in the platform's file browser.

    On POSIX this is a no-op that reports success: Canvas Bot's hidden
    directories are already dot-prefixed (``.manifest``), which is exactly how
    hiding works there.

    Parameters
    ----------
    path : str
        Directory to hide. Must already exist.

    Returns
    -------
    bool
        True if the directory is hidden (or hidden by naming convention).
        False if the attribute could not be set. Never raises.
    """
    if not IS_WINDOWS:
        return os.path.basename(os.path.normpath(path)).startswith(".")

    import ctypes

    try:
        ok = ctypes.windll.kernel32.SetFileAttributesW(path, _FILE_ATTRIBUTE_HIDDEN)
        if not ok:
            log.warning(f"Could not set hidden attribute on {path}")
        return bool(ok)
    except (AttributeError, OSError) as exc:
        log.warning(f"Could not set hidden attribute on {path} | {exc}")
        return False
