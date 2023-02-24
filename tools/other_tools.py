from config.read import read_config
from sorters.sorters import resource_node_regex

config = read_config()

def get_content_id_key_from_api_url(api_url):
    print("SDFSDFSDF", api_url)
    search = resource_node_regex.search(api_url)
    return config["content_ids"][search.group()]


