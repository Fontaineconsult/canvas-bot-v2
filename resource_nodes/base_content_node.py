from colorama import Fore, Style


class BaseCanvasContentNode:

    def __init__(self, parent, root, api_dict=None, item_id=None, title=None):
        self.api_dict = api_dict
        self.item_id = item_id
        self.title = title
        self.parent = parent
        self.root = root
        self.children = list()
        self.is_content = True
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




class BaseContentNode:

    def __init__(self, parent, root, api_dict=None, url=None, title=None, **kwargs):
        self.api_dict = api_dict
        self.is_canvas_file = False
        self.url = url
        self.title = title
        self.parent = parent
        self.root = root
        self.children = list()
        self.is_content = True
        self.item_id = hash(self.url) if self.url else None
        self._expand_api_dict_to_class_attributes()
        self.add_node_to_tree()
        self.root.manifest.add_item_to_manifest(self)

    def add_node_to_tree(self):
        if self.root:
            self.root.canvas_tree.add_node(self)
        else:
            Warning("No Root Node")

    def _expand_api_dict_to_class_attributes(self):
        if self.api_dict:
            self.is_canvas_file = True
            print(self.api_dict)
            self.id = self.api_dict['id']
            for key in self.api_dict:
                setattr(self, key, self.api_dict[key])


    def __str__(self):
        return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {self.url}){Style.RESET_ALL}"

    def __repr__(self):
        return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__}){Style.RESET_ALL}"