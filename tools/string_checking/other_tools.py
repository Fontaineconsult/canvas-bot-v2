import os
import re
import mimetypes
import warnings
from urllib import parse

from config.yaml_io import read_config
from sorters.sorters import resource_node_regex, video_file_content_regex, audio_file_content_regex

config = read_config()

def get_content_id_key_from_api_url(api_url):
    search = resource_node_regex.search(api_url)
    return config["content_ids"][search.group()]


def has_file_extension(filename, extension_class=None):

    if extension_class == "audio_files":
        return bool(audio_file_content_regex.match(filename))

    if extension_class == "video_files":
        return bool(video_file_content_regex.match(filename))

    return bool(re.search(r'\.\w+$', filename))



def remove_query_params_from_url(url):
    return url.split('?')[0]


def get_extension_from_filename(file_name):

    if not has_file_extension(file_name):
        return None
    return file_name.split('.')[-1] or None


def get_extension_from_mime_type(mime_type):
    return mimetypes.guess_extension(mime_type)


def create_long_path_file(long_path):
    # Convert to absolute path
    abs_path = os.path.abspath(long_path)

    # Add the \\?\ prefix
    extended_path = "\\\\?\\" + abs_path
    return extended_path


def create_filename_from_url(url):
    # Parse the URL
    print(url)
    parsed_url = parse.urlparse(url)
    # Extract query parameters
    query_params = parse.parse_qs(parsed_url.query)
    # Extract the filename from query parameters
    if 'filename' in query_params:
        filename = query_params['filename'][0]
    else:
        warnings.warn(f"No filename found in query parameters for {url}")
        return "No File Name Found"


    # Extract the extension from the URL path
    path = parsed_url.path
    extension = path.split('.')[-1]

    # Combine filename and extension
    complete_filename = f"{filename}.{extension}"

    return complete_filename


