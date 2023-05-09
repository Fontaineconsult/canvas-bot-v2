import os, json
import sys

import keyring, keyring.errors

try:
    import logging
    import tools.logger
    log = logging.getLogger(__name__)
except (AttributeError, ImportError):
    print("Can't import log profile. Logging disabled for credentials module.")



def save_canvas_api_key(api_key):
    keyring.set_password("ACCESS_TOKEN", "canvas_bot", api_key)
    log.info("Access Token for Canvas Bot Saved")
    print("Access Token for Canvas Bot Saved")


def delete_canvas_api_key():
    try:
        keyring.delete_password("ACCESS_TOKEN", "canvas_bot")
        log.info("Access Token for Canvas Bot Deleted")
        print("Access Token for Canvas Bot Deleted")
    except keyring.errors.PasswordDeleteError:
        print("Access Token found for Canvas Bot.")


def set_canvas_api_key_to_environment_variable():
    """
    Load and set the Canvas API Key to an environment variable.
    :return:
    """

    api_key = keyring.get_password("ACCESS_TOKEN", "canvas_bot")

    if api_key:
        os.environ["ACCESS_TOKEN"] = api_key
        log.info("Access Token for Canvas Bot Set")
        return True
    else:
        log.info("No Canvas Access Token Found")
        print("No Canvas Access Token Found")
        return False


def save_config_data(config_data=None, folder_only=False):
    """
    Save configuration data to a JSON file in the AppData folder.

    Args:
    config_data (dict): A dictionary containing the configuration data.
    app_name (str): The name of your application.
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

    try:
        with open(config_file_path, "w") as config_file:
            json.dump(config_data, config_file, indent=4)
    except OSError as exc:
        print("Couldn't write config data to %s" % app_folder)
        print("Program can't continue. See log file for details. Exiting now")
        log.exception("Can't write config data %s" % exc)
        sys.exit()


def load_config_data_from_appdata():
    """
    Load configuration data from a JSON file in the AppData folder.

    Returns:
    dict: A dictionary containing the configuration data.
    """
    # Get the AppData folder path
    appdata_path = os.environ.get("APPDATA")
    app_folder = os.path.join(appdata_path, "canvas bot")

    # check if the config file exists
    if not os.path.exists(os.path.join(app_folder, "config.json")):
        return False

    # Load the configuration data from the JSON file
    config_file_path = os.path.join(app_folder, "config.json")
    with open(config_file_path, "r") as config_file:
        log.info("Config File Loaded")
        config_data = json.load(config_file)

    # set each key in the config data to an environment variable
    for key, value in config_data.items():
        os.environ[key] = value
    return True


def delete_config_file_from_appdata():
    """
    Delete the configuration file from the AppData folder.
    """
    # Get the AppData folder path
    appdata_path = os.environ.get("APPDATA")
    app_folder = os.path.join(appdata_path, "canvas bot")

    # Delete the configuration file
    config_file_path = os.path.join(app_folder, "config.json")
    os.remove(config_file_path)
    log.info("Config File Deleted")


def save_youtube_api_key(youtube_key):

    keyring.set_password("youtube_for_canvasbot", "youtube_for_canvasbot", youtube_key)
    log.info("YouTube API Key Saved")
    print("YouTube API Key Saved")


def get_youtube_api_key():
        return keyring.get_password("youtube_for_canvasbot", "youtube_for_canvasbot")




def save_amara_api_key(amara_api_key):

    keyring.set_password("amara_for_canvasbot", "amara_for_canvasbot", amara_api_key)
    log.info("Amara API Key Saved")
    print("Amara API Key Saved")


def save_vimeo_api_key(vimeo_api_key):

    keyring.set_password("vimeo_for_canvasbot", "vimeo_for_canvasbot", vimeo_api_key)
    log.info("Vimeo API Key Saved")
    print("Vimeo API Key Saved")


