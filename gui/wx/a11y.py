"""Screen-reader speech for the wx GUI.

Speaks through a *real* screen reader (NVDA / JAWS / System Access / Dolphin /
PC-Talker / ZDSR) when one is running, and stays SILENT otherwise (never falls
back to the Windows SAPI/TTS voice).

CRITICAL — threading & COM:
Some screen readers (notably JAWS) are driven via a COM object. Calling that
COM object from the wx UI thread is unsafe:
  * a blocking COM call freezes the whole GUI (lock-up), and
  * hammering it (every announce re-probes is_active AND speaks) can crash the
    screen reader.
So ALL screen-reader interaction happens on a single dedicated worker thread
that:
  * calls CoInitialize once (correct COM apartment for the life of the object),
  * builds the accessible_output2 outputs once, on that thread,
  * consumes announcements from a queue.
The UI thread only enqueues text — it never touches COM — so a slow/hung screen
reader can never freeze the app, and there is no cross-apartment COM access.

Fail-safe: if anything goes wrong constructing or calling the outputs, speech is
disabled for the rest of the session rather than risking another lock-up.
"""

import logging
import queue
import threading

log = logging.getLogger(__name__)

# accessible_output2 output classes that are genuine screen readers. SAPI/TTS
# engines are excluded so we never speak without a screen reader present.
_SCREEN_READER_OUTPUTS = frozenset({
    "NVDA", "Jaws", "SystemAccess", "Dolphin", "PCTalker", "ZDSR",
    "WindowEyes", "Supernova",
})

# Sentinel used to tell the worker to stop.
_STOP = object()

_queue = None            # queue.Queue of (text, interrupt) | _STOP
_worker = None           # the speech thread
_started = False
_disabled = False        # set True permanently if speech proves unsafe
_lock = threading.Lock()
_available = False       # best-effort: was a screen reader seen at startup?


def _speech_worker():
    """Owns all COM/screen-reader interaction on one thread.

    Initializes COM, builds the outputs once, then serves the queue. Detection
    of the active output is cached briefly so we don't COM-probe on every
    message (JAWS's is_active() is itself a COM call).
    """
    global _available, _disabled
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception as exc:  # COM unavailable — disable speech, stay silent
        log.warning(f"CoInitialize failed; screen-reader speech disabled: {exc}")
        _disabled = True
        return

    try:
        import accessible_output2.outputs.auto
        auto = accessible_output2.outputs.auto.Auto()
        outputs = [o for o in auto.outputs
                   if type(o).__name__ in _SCREEN_READER_OUTPUTS]
        log.info("Screen-reader outputs: %s",
                 [type(o).__name__ for o in outputs])
    except Exception as exc:
        log.warning(f"accessible_output2 unavailable; speech disabled: {exc}")
        _disabled = True
        return

    cached = None          # last output found active
    cached_until = 0.0     # monotonic time the cache is valid to
    import time

    def active_output():
        nonlocal cached, cached_until
        now = time.monotonic()
        if cached is not None and now < cached_until:
            return cached
        found = None
        for o in outputs:
            try:
                if o.is_active():
                    found = o
                    break
            except Exception:
                continue
        cached = found
        cached_until = now + 2.0  # re-probe at most every 2s
        return found

    # Mark availability for is_available() once outputs are built.
    _available = bool(outputs)

    consecutive_errors = 0
    while True:
        item = _queue.get()
        if item is _STOP:
            break
        text, interrupt = item
        # Coalesce: if more messages are already queued, skip this one when it
        # is interruptible (the newer message will supersede it anyway). Keeps
        # us from backlogging the screen reader during rapid navigation.
        if interrupt and not _queue.empty():
            continue
        out = active_output()
        if out is None:
            continue
        try:
            out.speak(text, interrupt=interrupt)
            consecutive_errors = 0
        except Exception as exc:
            consecutive_errors += 1
            log.debug(f"speak failed ({consecutive_errors}): {exc}")
            # If the screen-reader bridge keeps failing, stop touching it so a
            # broken COM server can't be hammered into crashing.
            if consecutive_errors >= 3:
                log.warning("Disabling screen-reader speech after repeated failures")
                _disabled = True
                break

    try:
        pythoncom.CoUninitialize()
    except Exception:
        pass


def _ensure_started():
    """Start the speech worker once (lazily, from the UI thread)."""
    global _queue, _worker, _started
    if _started:
        return
    with _lock:
        if _started:
            return
        _started = True
        _queue = queue.Queue()
        _worker = threading.Thread(target=_speech_worker, daemon=True,
                                   name="cb-speech")
        _worker.start()


def announce(text, interrupt=False):
    """Queue ``text`` to be spoken by the screen reader, if one is running.

    Returns immediately — never blocks the UI thread on COM. Silent no-op when
    speech is disabled or no screen reader is active. ``interrupt=True`` lets
    the message supersede queued ones (matches screen-reader interrupt
    behavior).
    """
    if not text or _disabled:
        return
    _ensure_started()
    try:
        _queue.put_nowait((str(text), interrupt))
    except Exception:
        pass


def is_available():
    """Best-effort: True if a screen reader was detected.

    Starts the worker (which performs detection) and reports the last known
    result. May be False on the very first call before the worker has probed;
    callers use this only for non-critical logging.
    """
    _ensure_started()
    return _available and not _disabled


def shutdown(timeout=2.0):
    """Stop the speech thread cleanly (call once on app exit).

    Lets the worker CoUninitialize and drop its COM object before the
    interpreter tears down, avoiding shutdown-time COM races. Safe to call even
    if the worker never started.
    """
    if _queue is not None:
        try:
            _queue.put_nowait(_STOP)
        except Exception:
            pass
    if _worker is not None:
        _worker.join(timeout=timeout)
