from colorama import Fore, Style


from core.node_sorter import sort_nodes
from core.scraper import get_data_api_links_from_html, get_general_links_from_html_a_tag
from network.api import get_url



class Node:

    def __init__(self, parent, root, item_id=None, title=None):
        self.parent = parent
        self.root = root
        self.children = list()
        self.item_id = item_id
        self.title = title
        self.add_node_to_tree()

    def __str__(self):
        return f"<{Fore.WHITE}Node {self.__class__.__name__} {self.title[0:30] if self.title else self.item_id}{Style.RESET_ALL}>"

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


    def add_data_api_link_to_children(self, html):
        from core.node_factory import get_node_by_a_tag_match
        from tools.other_tools import get_content_id_key_from_api_url
        from resource_nodes.modules import Module

        data_api_links = self.get_data_api_links(html)

        for link in data_api_links:
            api_page = get_url(link[0])

            item_id = api_page[get_content_id_key_from_api_url(link[0])]

            if not self.root.manifest.id_exists(item_id):
                data_api_node = get_node_by_a_tag_match(link[0])
                if get_node_by_a_tag_match(link[0]) == Module:
                    # need to handle this differently
                    continue

                self.children.append(data_api_node(self, self.root, api_page))


    @staticmethod
    def get_html_body_links(html_body) -> list:
        if not html_body:
            return list()
        return get_general_links_from_html_a_tag(html_body)

    @staticmethod
    def get_data_api_links(html_body) -> list:
        if not html_body:
            return list()
        return get_data_api_links_from_html(html_body)