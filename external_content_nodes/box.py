import json
from colorama import Fore, Style, init
import requests
from bs4 import BeautifulSoup
import re

from colorama import Style, Fore

from config.yaml_io import read_config

from resource_nodes.content_nodes import FileStorageSite
from tools.string_checking.other_tools import get_extension_from_filename

init()
filters = read_config()['filters']

class BoxPage(FileStorageSite):

    def __init__(self, parent, root, api_dict=None, url=None, title=None, **kwargs):
        super().__init__(parent, root, api_dict, url, title, **kwargs)
        self.get_box_html_page()



    def __str__(self):
        return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {self.url}){Style.RESET_ALL}"

    def __repr__(self):
        return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__}){Style.RESET_ALL}"


    def get_box_html_page(self):
        from core.node_factory import get_content_node
        page_request = requests.get(self.url)

        if page_request:
            page_html = BeautifulSoup(page_request.content, features="lxml")

            page_scripts = page_html.find_all(filters[self.__class__.__name__])
            expression = re.compile("Box\.postStreamData")
            items_expression = re.compile('"items":\[\{.*.}]')

            for script in page_scripts:
                if expression.search(script.text):

                    clean_text = script.text.replace("'","")

                    items = items_expression.search(clean_text)


                    try:
                        raw_string_dict = f"{{{items.group()}}}"
                        json_dict = json.loads(raw_string_dict)

                    except json.decoder.JSONDecodeError:
                        raw_string_dict = raw_string_dict + "}"
                        json_dict = json.loads(raw_string_dict)

                    except AttributeError:
                        print(f"{Fore.RED}No items found in {self.url}{Style.RESET_ALL}")
                        continue

                    for item in json_dict['items']:

                        content_node = get_content_node(item['name'])
                        content_node.mime_class = get_extension_from_filename(item['name'])
                        self.children.append(content_node(self, self.root, None, self.url, item['name']))
