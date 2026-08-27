import logging.config
import getpass
import os
import stat
import sys
import threading
import uuid
import logging
import re
from network.set_config import save_config_data

log_save_location = save_config_data(folder_only=True)

print(f"Log save location: {log_save_location}")


# Session context filter — injects username and session ID into every log record
_session_id = uuid.uuid4().hex[:8]

class SessionContextFilter(logging.Filter):
    def filter(self, record):
        record.user = getpass.getuser()
        record.session = _session_id
        return True


class _RedactSecrets(logging.Filter):
    """Scrub Canvas access tokens from every record on every handler.

    Legacy Canvas auth rides in URL query strings, and requests exceptions
    embed full URLs — without this, a connection error can write the token
    into canvas_bot.log verbatim.
    """

    _TOKEN = re.compile(r"access_token=[^&\s'\"]+")

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if "access_token=" in message:
            record.msg = self._TOKEN.sub("access_token=***", message)
            record.args = None
        return True


LOGGING_CONFIG = {
    'version': 1,
    'filters': {
        'redact': {'()': _RedactSecrets},
    },
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(user)s - %(session)s - %(name)s - %(levelname)s - %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'level': 'DEBUG',
            'filters': ['redact'],
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'default',
            'level': 'DEBUG',
            'filename': os.path.join(log_save_location, "canvas_bot.log"),
            'mode': 'a',
            'encoding': 'utf-8',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'filters': ['redact'],
        },
    },
    'loggers': {
        '': {  # Root logger
            'handlers': ['file'],
            'level': 'DEBUG',
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)

# Apply session filter to all handlers
_session_filter = SessionContextFilter()
for handler in logging.root.handlers:
    handler.addFilter(_session_filter)

# Global exception hook — logs any unhandled exception (with its full
# traceback) to the log file. wx event-handler exceptions also arrive here
# via PyErr_Print.
_unhandled_log = logging.getLogger('unhandled')

def _excepthook(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    _unhandled_log.error(f"Unhandled {exc_type.__name__}: {exc_value}",
                         exc_info=(exc_type, exc_value, exc_tb))

sys.excepthook = _excepthook


# Thread exceptions bypass sys.excepthook entirely (Python routes them to
# threading.excepthook, which only prints to stderr). The app runs scans,
# replaces, token validation, and speech on worker threads — an uncaught
# crash there must still reach the log file.
def _thread_excepthook(args):
    if args.exc_type is SystemExit:
        return  # matches the default hook's behavior
    name = args.thread.name if args.thread is not None else "?"
    _unhandled_log.error(
        f"Unhandled {args.exc_type.__name__} in thread {name}: {args.exc_value}",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

threading.excepthook = _thread_excepthook

# Best-effort log file permission restriction (limited on Windows,
# but %APPDATA% is already per-user)
_log_file = os.path.join(log_save_location, "canvas_bot.log")
try:
    if os.path.exists(_log_file):
        os.chmod(_log_file, stat.S_IRUSR | stat.S_IWUSR)
except OSError:
    pass
