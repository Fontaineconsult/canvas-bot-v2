import logging.config
import os
import logging
from network.cred import save_config_data



log_save_location = save_config_data(folder_only=True)

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
            'filename': os.path.join(log_save_location, "canvas_bot.log"),  # Specify the location of the log file here
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



# def set_logger():
#
#
#     log_save_location = save_config_data(folder_only=True)
#
#     LOGGING_CONFIG = {
#         'version': 1,
#         'formatters': {
#             'default': {
#                 'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#             },
#         },
#         'handlers': {
#             'console': {
#                 'class': 'logging.StreamHandler',
#                 'formatter': 'default',
#                 'level': 'DEBUG',
#             },
#             'file': {
#                 'class': 'logging.FileHandler',
#                 'formatter': 'default',
#                 'level': 'DEBUG',
#                 'filename': os.path.join(log_save_location, "canvas_bot.log"),  # Specify the location of the log file here
#                 'mode': 'a',  # 'a' stands for 'append', which means new log messages will be appended to the file
#                 'encoding': 'utf-8',
#             },
#         },
#         'loggers': {
#             '': {  # Root logger
#                 'handlers': ['file'],
#                 'level': 'DEBUG',
#             },
#         },
#     }
#
#     logging.config.dictConfig(LOGGING_CONFIG)
#
