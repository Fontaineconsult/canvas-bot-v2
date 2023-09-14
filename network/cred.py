import atexit
import os, json
import sys

import keyring, keyring.errors

from network.studio_api import refresh_studio_token

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


def save_canvas_studio_client_keys(studio_client_id, studio_client_secret):
    keyring.set_password("STUDIO_CLIENT_ID", "canvas_bot", studio_client_id)
    keyring.set_password("STUDIO_CLIENT_SECRET", "canvas_bot", studio_client_secret)
    print("Canvas Studio Client Keys Saved")



def delete_canvas_studio_client_keys():
    try:
        keyring.delete_password("STUDIO_CLIENT_ID", "canvas_bot")
        keyring.delete_password("STUDIO_CLIENT_SECRET", "canvas_bot")
        log.info("Studio Client Keys for Canvas Bot Deleted")
        print("Studio Client Keys for Canvas Bot Deleted")
    except keyring.errors.PasswordDeleteError:
        print("Studio Client Keys found for Canvas Bot.")



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


def get_canvas_studio_client_credentials():
    """
    Load and set the Canvas Studio Client Keys to environment variables.
    :return:
    """

    studio_client_id = keyring.get_password("STUDIO_CLIENT_ID", "canvas_bot")
    studio_client_secret = keyring.get_password("STUDIO_CLIENT_SECRET", "canvas_bot")

    if studio_client_id and studio_client_secret:
        return studio_client_id, studio_client_secret
    else:
        log.info("No Studio Client Keys Found")
        print("No Studio Client Keys Found")
        return False




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


def clear_env_settings():
    del os.environ["ACCESS_TOKEN"]



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


atexit.register(clear_env_settings)
