import animation
from core.node_factory import get_content_node
from network.api import get_media_objects

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

        api_dict = self.api_request(self.course_id)
        if api_dict:
            for media_object_dict in api_dict:
                media_node = get_content_node(None, media_object_dict)
                self._expand_api_dict_to_class_attributes(media_object_dict)
                media_node = media_node(self, self.parent, media_object_dict)
                media_node.url = media_object_dict['media_sources'][-1]['url']
                self.children.append(media_node)

