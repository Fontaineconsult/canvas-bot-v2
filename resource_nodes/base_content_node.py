from colorama import Fore, Style


class BaseContentNode:

    def __init__(self, parent, root, item_id=None, title=None):
        self.item_id = item_id
        self.title = title
        self.parent = parent
        self.root = root
        self.children = list()
        self.add_node_to_tree()


    def add_node_to_tree(self):
        if self.root:
            self.root.canvas_tree.add_node(self)
        else:
            Warning("No Root Node")

    @classmethod
    def _expand_api_dict_to_class_attributes(cls, api_dict):
        for key in api_dict:
            setattr(cls, key, api_dict[key])

    def __str__(self):
        return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {self.title}){Style.RESET_ALL}"

    def __repr__(self):
        return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {self.item_id}){Style.RESET_ALL}"