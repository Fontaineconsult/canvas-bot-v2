from colorama import Fore, Style, init
from urllib.parse import unquote_plus
init()


class BaseContentNode:

    """
    Base class for all content nodes. Content nodes contain the information for an item of instructional content.
    Examples include, documents, videos, and links.
    """

    def __init__(self, parent, root,
                 api_dict=None,
                 url=None,
                 title=None,
                 captioned=False,
                 **kwargs):
        self.api_dict = api_dict
        self.is_canvas_file = False
        self.is_canvas_studio_file = False
        self.url = url
        self.file_name = None
        self.download_url = None
        self.download_url_is_manifest = False
        self.title = title
        self.parent = parent
        self.captioned = captioned
        self.root = root
        self.children = list()
        self.is_content = True
        self.item_id = self.derive_id()
        self._expand_api_dict_to_class_attributes()
        self.add_node_to_tree()
        self.root.manifest.add_item_to_manifest(self)


    def derive_id(self):
        if self.api_dict:
            if self.api_dict.get('id'):
                return self.api_dict.get('id')
        else:
            if self.url and self.title:
                return hash(self.url + self.title)
            if self.url and not self.title:
                return hash(self.url)
            if not self.url and self.title:
                return hash(self.title)
            if not self.url and not self.title:
                Warning(f"Can't derive ID {self}",)


    def add_node_to_tree(self):

        if self.root.root_node:
            self.root.canvas_tree.add_node(self)
        else:
            Warning("No Root Node")

    def _expand_api_dict_to_class_attributes(self):
        if self.api_dict:
            self.is_canvas_file = True

            for key in self.api_dict:
                setattr(self, key, self.api_dict[key])

            self.item_id = self.api_dict['id'] if self.api_dict.get('id') else self.api_dict['media_id']
            # Prefer display_name (human-readable) over filename (URL-encoded)
            # Fallback chain: display_name -> title -> filename (decoded)
            if self.api_dict.get('display_name'):
                self.title = self.api_dict['display_name']
            elif self.api_dict.get('title'):
                self.title = self.api_dict['title']
            elif self.api_dict.get('filename'):
                # URL-decode filename as last resort (converts + to spaces)
                self.title = unquote_plus(self.api_dict['filename'])



    def __str__(self):
        from core.content_scaffolds import is_hidden

        return f"{Fore.LIGHTWHITE_EX}( {self.__class__.__name__} {'hidden' if is_hidden(self) else 'visible'} {self.url if self.url else self.title} ){Style.RESET_ALL}"

    def __repr__(self):

        return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__}){Style.RESET_ALL}"