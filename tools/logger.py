import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'level': 'DEBUG',
        },
        'file': {
            'class': 'logging.FileHandler',
            'formatter': 'default',
            'level': 'DEBUG',
            'filename': r'C:\Users\DanielPC\Desktop\Servers\canvas-bot-v2\application.log',  # Specify the location of the log file here
            'mode': 'a',  # 'a' stands for 'append', which means new log messages will be appended to the file
            'encoding': 'utf-8',
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