from network.api import get_discussions, get_discussion
from resource_nodes.base_node import Node
from tools.animation import animate


class Discussions(Node):

    """
    This class is a container for all discussions in a course.
    """

    def __init__(self, course_id, parent):

        super().__init__(parent, parent)
        self.course_id = course_id
        self.api_request = get_discussions
        self.api_request_content = None
        self.get_all_items()

    @animate('Importing Discussions')
    def get_all_items(self):

        api_request = self.api_request(self.course_id)
        if api_request:
            for module_dict in api_request:
                self.children.append(Discussion(self, self.parent, module_dict))


class Discussion(Node):

    """
    This class is a container for a single discussion in a course.
    """

    def __init__(self, parent, root, api_dict, **kwargs):
        if not kwargs.get("bypass_get_url") is True:
            if api_dict:
                api_dict = get_discussion(root.course_id, api_dict['id'])

        if api_dict:
            super().__init__(parent, root, api_dict['id'], api_dict['title'])
            self.root.manifest.add_item_to_manifest(self)
            self._expand_api_dict_to_class_attributes(api_dict)
            try:
                self.add_data_api_link_to_children(self.message)
                self.add_content_nodes_to_children(self.message)
            except AttributeError:
                pass

