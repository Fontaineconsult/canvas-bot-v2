from colorama import Fore, Style

from network.api import get_discussions, get_files
from resource_nodes.base_content_node import BaseContentNode
from resource_nodes.base_node import Node


class Files(Node):

    def __init__(self, course_id, parent):

        super().__init__(parent, parent)
        self.course_id = course_id
        self.api_request = get_files
        self.api_request_content = None
        self.get_all_items()

    def get_all_items(self):

        api_request = self.api_request(self.course_id)

        for file_dict in api_request:
            self.children.append(File(self, self.parent, file_dict))


class File(BaseContentNode):

    def __init__(self, parent, root, api_dict):
        super().__init__(parent, root, api_dict['id'], api_dict['filename'])
        self.api_dict = api_dict
        self.root.manifest.add_item_to_manifest(self)
        self._expand_api_dict_to_class_attributes(self.api_dict)