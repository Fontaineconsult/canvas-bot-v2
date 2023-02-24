from colorama import Fore, Style

from network.api import get_discussions, get_files, get_file
from resource_nodes.base_content_node import BaseCanvasContentNode
from resource_nodes.base_node import Node


class CanvasFiles(Node):

    def __init__(self, course_id, parent):

        super().__init__(parent, parent)
        self.course_id = course_id
        self.api_request = get_files
        self.api_request_content = None
        self.get_all_items()

    def get_all_items(self):

        api_request = self.api_request(self.course_id)
        if api_request:
            for file_dict in api_request:
                self.children.append(CanvasFile(self, self.parent, file_dict))


class CanvasFile(BaseCanvasContentNode):

    def __init__(self, parent, root, api_dict):
        canvas_file_dict = get_file(root.course_id, api_dict['id'])
        super().__init__(parent, root, canvas_file_dict['id'], canvas_file_dict['filename'])
        self.root.manifest.add_item_to_manifest(self)
        self._expand_api_dict_to_class_attributes(canvas_file_dict)