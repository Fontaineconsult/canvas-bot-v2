"""Screen-reader speech for the wx GUI.

Wraps ``accessible_output2`` so the rest of the GUI can call ``announce(text)``
without worrying about whether a screen reader is present. accessible_output2's
Auto output speaks through whichever of NVDA / JAWS / System Access / SAPI5 is
available, so this works both with a running screen reader and (via SAPI5) on a
plain desktop.

If the library is missing or no output can be constructed, every call becomes a
silent no-op — the GUI still works, it just doesn't speak.

Native wx controls already expose their name/role/state to screen readers via
MSAA; this module is only for *dynamic* events a screen reader can't infer from
focus alone: scan progress, replace milestones, validation results, completion.
"""

import logging

log = logging.getLogger(__name__)

_output = None
_initialized = False


def _ensure():
    """Lazily construct the accessible_output2 Auto output exactly once."""
    global _output, _initialized
    if _initialized:
        return _output
    _initialized = True
    try:
        import accessible_output2.outputs.auto
        _output = accessible_output2.outputs.auto.Auto()
        log.info("accessible_output2 initialized")
    except Exception as exc:  # library missing, no output available, etc.
        log.warning(f"Screen-reader output unavailable: {exc}")
        _output = None
    return _output


def announce(text, interrupt=False):
    """Speak ``text`` through the active screen reader / SAPI.

    ``interrupt=True`` cuts off any in-progress speech (use for rapidly-changing
    status so announcements don't pile up). Never raises — speech failures are
    swallowed so a flaky TTS path can't break the UI.
    """
    if not text:
        return
    out = _ensure()
    if out is None:
        return
    try:
        out.speak(str(text), interrupt=interrupt)
    except Exception as exc:  # pragma: no cover - defensive
        log.debug(f"announce failed: {exc}")


def is_available():
    """True when a speech output was successfully constructed."""
    return _ensure() is not None
