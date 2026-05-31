"""Screen-reader speech for the wx GUI.

Speaks through a *real* screen reader (NVDA / JAWS / System Access / Dolphin /
PC-Talker / ZDSR) when one is running, and stays SILENT otherwise.

Why not accessible_output2's Auto() directly: Auto() includes a SAPI5 output
whose ``is_active()`` is always True, so on a plain desktop (no screen reader)
the app would talk to itself through the Windows TTS voice. We deliberately
exclude SAPI5 (and any non-screen-reader TTS) and only emit when an actual
screen reader is present — speech is a redundant channel layered on top of the
native MSAA accessibility, not a feature for sighted users.

If the library is missing, or no screen reader is active, every call is a
silent no-op.
"""

import logging

log = logging.getLogger(__name__)

# accessible_output2 output classes that are genuine screen readers. SAPI5
# (Windows TTS) and any other pure-TTS engine are intentionally excluded so we
# never speak on a machine without a screen reader.
_SCREEN_READER_OUTPUTS = frozenset({
    "NVDA", "Jaws", "SystemAccess", "Dolphin", "PCTalker", "ZDSR",
    "WindowEyes", "Supernova",
})

_outputs = None        # list of candidate screen-reader output objects
_initialized = False


def _ensure():
    """Build the list of screen-reader outputs once (excludes SAPI/TTS)."""
    global _outputs, _initialized
    if _initialized:
        return _outputs
    _initialized = True
    try:
        import accessible_output2.outputs.auto
        auto = accessible_output2.outputs.auto.Auto()
        _outputs = [o for o in auto.outputs
                    if type(o).__name__ in _SCREEN_READER_OUTPUTS]
        log.info("Screen-reader outputs: %s",
                 [type(o).__name__ for o in _outputs])
    except Exception as exc:
        log.warning(f"accessible_output2 unavailable: {exc}")
        _outputs = []
    return _outputs


def _active_output():
    """Return the first currently-running screen-reader output, or None."""
    for o in _ensure():
        try:
            if o.is_active():
                return o
        except Exception:
            continue
    return None


def announce(text, interrupt=False):
    """Speak ``text`` — ONLY if a real screen reader is currently running.

    No screen reader active -> silent no-op (never falls back to the Windows
    TTS voice). ``interrupt=True`` cuts off in-progress speech. Never raises.
    """
    if not text:
        return
    out = _active_output()
    if out is None:
        return
    try:
        out.speak(str(text), interrupt=interrupt)
    except Exception as exc:  # pragma: no cover - defensive
        log.debug(f"announce failed: {exc}")


def is_available():
    """True only when a real screen reader is currently active."""
    return _active_output() is not None
