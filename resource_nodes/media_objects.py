from core.node_factory import get_content_node
from network.api import get_media_objects

from resource_nodes.base_node import Node
from tools.animation import animate


class CanvasMediaObjects(Node):

    """
    This class is a container for all media objects in a course. In Canvas Media Objects are usually videos
    """

    def __init__(self, course_id, parent):

        super().__init__(parent, parent)
        self.course_id = course_id
        self.api_request = get_media_objects
        self.api_request_content = None
        self.get_all_items()

    @animate('Importing Media Objects')
    def get_all_items(self):

        api_dict = self.api_request(self.course_id)

        if api_dict:
            for media_object_dict in api_dict:
                media_node = get_content_node(None, media_object_dict)
                self._expand_api_dict_to_class_attributes(media_object_dict)
                if len(media_object_dict['media_sources']) > 0:
                    media_node = media_node(self, self.parent, media_object_dict)
                    media_node.url = media_object_dict['media_sources'][-1]['url']
                    media_node.item_id = media_object_dict['media_id']
                    print(media_object_dict)
                    self.children.append(media_node)

