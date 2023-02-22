
from resource_nodes.base_node import Node

from network.api import get_modules, get_module_items, get_url



class Modules(Node):

    def __init__(self, course_id, parent):

        super().__init__(parent, parent)
        self.course_id = course_id
        self.api_request = get_modules
        self.api_request_content = None
        self.get_all_items()

    def get_all_items(self):

        api_request = self.api_request(self.course_id)
        for module_dict in api_request:
            self.children.append(Module(self, self.parent, module_dict))



class Module(Node):

    def __init__(self, parent, root, api_dict):
        super().__init__(parent, root, api_dict['id'], api_dict['name'])
        self.api_dict = api_dict
        self.identify_content()

    def identify_content(self):
        from core.node_factory import get_node
        module_items = get_module_items(self.api_dict['items_url'])
        for item in module_items:
            ContentNode = get_node(item['type'])
            if ContentNode:
                module_item_dict = get_url(item['url'])
                self.children.append(ContentNode(self, self.root, module_item_dict))
