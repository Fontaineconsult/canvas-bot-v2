import animation
from colorama import Fore, Style

from core.node_factory import get_content_node
from network.api import get_media_objects
from resource_nodes.base_content_node import BaseCanvasContentNode, BaseContentNode
from resource_nodes.base_node import Node


class CanvasMediaObjects(Node):

    def __init__(self, course_id, parent):

        super().__init__(parent, parent)
        self.course_id = course_id
        self.api_request = get_media_objects
        self.api_request_content = None
        self.get_all_items()

    @animation.wait('spinner')
    def get_all_items(self):

        api_request = self.api_request(self.course_id)

        for media_object_dict in api_request:
            media_node = get_content_node(None, media_object_dict)
            self.children.append(media_node(self, self.parent, media_object_dict))


# class CanvasMediaObject(BaseContentNode):
#
#     def __init__(self, parent, root, api_dict):
#         super().__init__(parent, root, api_dict['media_id'], api_dict['title'])
#         self.api_dict = api_dict
#         self.root.manifest.add_item_to_manifest(self)
#         self._expand_api_dict_to_class_attributes(self.api_dict)
