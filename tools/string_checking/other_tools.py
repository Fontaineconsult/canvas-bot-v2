import re
import mimetypes
from config.yaml_io import read_config
from sorters.sorters import resource_node_regex

config = read_config()

def get_content_id_key_from_api_url(api_url):
    search = resource_node_regex.search(api_url)
    return config["content_ids"][search.group()]


def has_file_extension(filename):
    return bool(re.search(r'\.\w+', filename))


def remove_query_params_from_url(url):
    return url.split('?')[0]


def get_extension_from_filename(file_name):

    if not has_file_extension(file_name):
        return None
    return file_name.split('.')[-1] or None

