import re

from config.read import read_config
from sorters.sorters import resource_node_regex

config = read_config()

def get_content_id_key_from_api_url(api_url):
    search = resource_node_regex.search(api_url)
    return config["content_ids"][search.group()]


def has_file_extension(filename):
    return bool(re.search(r'\.\w+', filename))

