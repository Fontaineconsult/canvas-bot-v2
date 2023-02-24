from network.api import get_quizzes, get_quiz
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
        if api_request:
            for module_dict in api_request:
                self.children.append(Quiz(self, self.parent, module_dict))


class Quiz(Node):

    def __init__(self, parent, root, api_dict):
        quiz_dict = get_quiz(root.course_id, api_dict['id'])
        super().__init__(parent, root, quiz_dict['id'], quiz_dict['title'])
        self.root.manifest.add_item_to_manifest(self)
        self._expand_api_dict_to_class_attributes(quiz_dict)
        self.add_data_api_link_to_children(self.description)