import json
import os
import sys

import logging
import tools.logger
log = logging.getLogger(__name__)


def save_config_data(config_data=None, folder_only=False):

    """
    Save configuration data to a JSON file in the AppData folder.

    Args:
    config_data (dict): A dictionary containing the configuration data.
    """
    # Get the AppData folder path
    appdata_path = os.environ.get("APPDATA")
    app_folder = os.path.join(appdata_path, "canvas bot")

    # Create the application folder if it doesn't exist
    try:
        if not os.path.exists(app_folder):
            os.makedirs(app_folder)
    except OSError as exc:
        print("Creation of the app data directory %s failed" % app_folder)
        print("Program can't continue. See log file for details. Exiting now")
        log.exception("Creation of the app data directory failed with error %s" % exc)
        sys.exit()

    if folder_only:
        return app_folder

    # Save the configuration data as a JSON file
    config_file_path = os.path.join(app_folder, "config.json")

    # If config.json exists, read its content and merge with new data
    if os.path.exists(config_file_path):
        with open(config_file_path, "r") as config_file:
            existing_data = json.load(config_file)
            existing_data.update(config_data)  # Merge new data with existing data
        config_data = existing_data

    try:
        with open(config_file_path, "w") as config_file:
            json.dump(config_data, config_file, indent=4)
    except OSError as exc:
        print("Couldn't write config data to %s" % config_file_path)
        print("Program can't continue. See log file for details. Exiting now")
        log.exception("Can't write config data %s" % exc)
        sys.exit()
