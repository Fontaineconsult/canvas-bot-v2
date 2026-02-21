import logging.config
import getpass
import os
import stat
import uuid
import logging
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


LOGGING_CONFIG = {
    'version': 1,
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

# Best-effort log file permission restriction (limited on Windows,
# but %APPDATA% is already per-user)
_log_file = os.path.join(log_save_location, "canvas_bot.log")
try:
    if os.path.exists(_log_file):
        os.chmod(_log_file, stat.S_IRUSR | stat.S_IWUSR)
except OSError:
    pass
