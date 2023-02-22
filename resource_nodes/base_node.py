from colorama import Fore, Style

from core.node_sorter import sort_nodes
from core.scraper import get_general_links_from_html, get_data_api_links_from_html


class Node:

    def __init__(self, parent, root, item_id=None, title=None):
        self.parent = parent
        self.root = root
        self.children = list()
        self.item_id = item_id
        self.title = title
        self.add_node_to_tree()

    def __str__(self):
        return f"<{Fore.WHITE}Node {self.__class__.__name__} {self.title if self.title else self.item_id}{Style.RESET_ALL}>"

    def __repr__(self):
        return f"<{Fore.WHITE} {self.__class__.__name__} {self.item_id}{Style.RESET_ALL}>"


    def add_node_to_tree(self):
        if self.root:
            self.root.canvas_tree.add_node(self)
        else:
            Warning("No Root Node")

    def _expand_api_dict_to_class_attributes(self, api_dict):
        for key in api_dict:
            setattr(self, key, api_dict[key])

    @staticmethod
    def get_html_body_links(html_body):
        return get_general_links_from_html(html_body)

    @staticmethod
    def get_data_api_links(html_body):
        return get_data_api_links_from_html(html_body)