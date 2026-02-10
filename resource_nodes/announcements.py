from network.api import get_announcements
from resource_nodes.base_node import Node
from tools.animation import animate


class Announcements(Node):

    """
    This class is a container for all announcements in a course.
    """

    def __init__(self, course_id, parent):

        super().__init__(parent, parent)
        self.course_id = course_id

        self.api_request = get_announcements
        self.api_request_content = None
        self.get_all_items()

    @animate('Importing Announcements')
    def get_all_items(self):

        api_request = self.api_request(self.course_id)
        if api_request:
            for module_dict in api_request:
                self.children.append(Announcement(self, self.parent, module_dict))



class Announcement(Node):

    def __init__(self, parent, root, api_dict):
        super().__init__(parent, root, api_dict['id'], api_dict['title'])
        self.root.manifest.add_item_to_manifest(self)
        self.api_dict = api_dict
        self._expand_api_dict_to_class_attributes(self.api_dict)
        try:
            self.add_content_nodes_to_children(self.message)
        except AttributeError:
            pass