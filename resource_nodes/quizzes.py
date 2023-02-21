from network.api import get_quizzes
from resource_nodes.base_node import Node


class Quizzes(Node):


    def __init__(self, course_id, parent):

        super().__init__(parent, parent)
        self.course_id = course_id
        self.api_request = get_quizzes
        self.api_request_content = None
        self.get_all_items()

    def get_all_items(self):

        api_request = self.api_request(self.course_id)

        for module_dict in api_request:

            pass
            self.children.append(Quiz(self, self.parent, module_dict))


class Quiz(Node):

    def __init__(self, parent, root, api_dict):
        super().__init__(parent, root, api_dict['id'], api_dict['title'])
        self.api_dict = api_dict
        self.root.manifest.add_item_to_manifest(self)
        self._expand_api_dict_to_class_attributes(self.api_dict)