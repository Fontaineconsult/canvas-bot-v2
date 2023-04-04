import os, json
import keyring, keyring.errors


def save_canvas_api_key(api_key):
    keyring.set_password("ACCESS_TOKEN", "canvas_bot", api_key)
    print("API Key for Canvas Bot Saved")

def delete_canvas_api_key():
    try:
        keyring.delete_password("ACCESS_TOKEN", "canvas_bot")
        print("API Key for Canvas Bot Deleted")
    except keyring.errors.PasswordDeleteError:
        print("No API key found for Canvas Bot.")



def set_canvas_api_key_to_environment_variable():
    """
    Load and set the Canvas API Key to an environment variable.
    :return:
    """

    api_key = keyring.get_password("ACCESS_TOKEN", "canvas_bot")

    if api_key:
        os.environ["ACCESS_TOKEN"] = api_key
        return True
    else:
        print("No Canvas API Key Found")
        return False

def save_config_data(config_data):
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
    if not os.path.exists(app_folder):
        os.makedirs(app_folder)

    # Save the configuration data as a JSON file
    config_file_path = os.path.join(app_folder, "config.json")
    with open(config_file_path, "w") as config_file:
        json.dump(config_data, config_file, indent=4)


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

