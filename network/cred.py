import atexit
import os, json

import keyring, keyring.errors


import logging
import tools.logger
log = logging.getLogger(__name__)


# try:
#     import logging
#     import tools.logger
#     log = logging.getLogger(__name__)
# except (AttributeError, ImportError):
#     print("Can't import log profile. Logging disabled for credentials module.")



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
    except keyring.errors.PasswordDeleteError as exc:
        print(exc)




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




def set_canvas_studio_api_key_to_environment_variable(token=None, re_auth=None):

    if token and re_auth:
        save_canvas_studio_tokens(token, re_auth)

    studio_token, studio_re_auth_token = get_canvas_studio_tokens()

    if studio_token and studio_re_auth_token:
        os.environ["CANVAS_STUDIO_TOKEN"] = studio_token
        os.environ["CANVAS_STUDIO_RE_AUTH_TOKEN"] = studio_re_auth_token
        log.info("Studio Tokens for Canvas Bot Set")
        return True
    else:
        log.info("No Studio Tokens Found")
        print("No Studio Tokens Found")
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


def save_canvas_studio_tokens(canvas_studio_token, canvas_studio_re_auth_token):
    """
    Save the Canvas Studio tokens to the environment variables.
    :param token:
    :param re_auth_token:
    :return:
    """
    keyring.set_password("CANVAS_STUDIO_TOKEN", "canvas_bot", canvas_studio_token)
    keyring.set_password("CANVAS_STUDIO_RE_AUTH_TOKEN", "canvas_bot", canvas_studio_re_auth_token)
    log.info("Studio Tokens for Canvas Bot Saved")
    print("Studio Tokens for Canvas Bot Saved")



def get_canvas_studio_tokens():
    """
    Save the Canvas Studio tokens to the environment variables.
    :param token:
    :param re_auth_token:
    :return:
    """
    studio_token = keyring.get_password("CANVAS_STUDIO_TOKEN", "canvas_bot")
    studio_re_auth_token = keyring.get_password("CANVAS_STUDIO_RE_AUTH_TOKEN", "canvas_bot")
    if studio_token and studio_re_auth_token:
        return studio_token, studio_re_auth_token
    else:
        log.info("No Studio Client Keys Found")
        print("No Studio Client Keys Found")
        return False, False


def delete_canvas_studio_tokens():
    try:
        keyring.delete_password("CANVAS_STUDIO_TOKEN", "canvas_bot")
        keyring.delete_password("CANVAS_STUDIO_RE_AUTH_TOKEN", "canvas_bot")
        log.info("Access Token for Canvas Bot Deleted")
        print("Access Token for Canvas Bot Deleted")
    except keyring.errors.PasswordDeleteError as exc:
        print(exc)


def check_config_status():
    """
    Check if Canvas Bot configuration is functional.

    Returns a tuple of (ok, message) where ok is True if the config is ready
    to use, and message is a human-readable status string.
    """
    appdata_path = os.environ.get("APPDATA", "")
    config_path = os.path.join(appdata_path, "canvas bot", "config.json")

    if not os.path.exists(config_path):
        return False, "Not Configured — click Reset Config to set up Canvas instance"

    api_key = keyring.get_password("ACCESS_TOKEN", "canvas_bot")
    if not api_key:
        return False, "No API Token — click Reset Config to set your access token"

    return True, "Ready"


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
        os.environ[key] = str(value)
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
    try:
        os.remove(config_file_path)
        log.info("Config File Deleted")
    except FileNotFoundError:
        log.exception("Config File Not Found -- Not Deleting")


def clear_env_settings():
    try:
        del os.environ["ACCESS_TOKEN"]
        del os.environ["CANVAS_STUDIO_TOKEN"]
        del os.environ["CANVAS_STUDIO_RE_AUTH_TOKEN"]
    except KeyError:
        pass


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
