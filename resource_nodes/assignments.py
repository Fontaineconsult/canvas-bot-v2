from network.api import get_assignments, get_assignment
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
        assignment_dict = get_assignment(root.course_id, api_dict['id'])
        super().__init__(parent, root, assignment_dict['id'])
        self.root.manifest.add_item_to_manifest(self)
        self._expand_api_dict_to_class_attributes(assignment_dict)
        self.add_data_api_link_to_children(self.description)