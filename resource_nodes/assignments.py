from datetime import datetime
from network.api import get_assignments, get_assignment
from resource_nodes.base_node import Node
from tools.animation import animate


class Assignments(Node):

    """
    This class is a container for all assignments in a course.
    """

    def __init__(self, course_id, parent):
        super().__init__(parent, parent)
        self.course_id = course_id

        self.api_request = get_assignments
        self.api_request_content = None
        self.get_all_items()

    @animate('Importing Assignments')
    def get_all_items(self):

        api_request = self.api_request(self.course_id)

        if api_request:
            for module_dict in api_request:
                self.children.append(Assignment(self, self.parent, module_dict))


class Assignment(Node):

    def __init__(self, parent, root, api_dict, **kwargs):
        if not kwargs.get("bypass_get_url") is True:
            api_dict = get_assignment(root.course_id, api_dict['id'])

        if api_dict:
            if api_dict.get('due_at'):
                date_obj = datetime.strptime(api_dict['due_at'], "%Y-%m-%dT%H:%M:%SZ")
                assignment_title = f"Assignment {api_dict['position']} | Due: {date_obj.strftime('%d-%m-%Y')}"
            else:
                assignment_title = f"Assignment {api_dict['position']} | No Due Date Set"
            super().__init__(parent, root, api_dict['id'], assignment_title)
            self.root.manifest.add_item_to_manifest(self)
            self._expand_api_dict_to_class_attributes(api_dict)
            try:
                self.add_data_api_link_to_children(self.description)
                self.add_content_nodes_to_children(self.description)
            except AttributeError:
                pass