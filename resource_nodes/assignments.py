from network.api import get_assignments
from resource_nodes.base_node import Node


class Assignments(Node):

    def __init__(self, course_id, parent):
        super().__init__(parent, parent)
        self.course_id = course_id
        self.api_request = get_assignments
        self.api_request_content = None
        self.get_all_items()

    def get_all_items(self):

        api_request = self.api_request(self.course_id)

        for module_dict in api_request:

            self.children.append(Assignment(self, self.parent, module_dict))


class Assignment(Node):

    def __init__(self, parent, root, api_dict):
        super().__init__(parent, root, api_dict['id'])
        self.api_dict = api_dict
