
from tools.animation import animate
from resource_nodes.base_node import Node
from network.api import get_modules, get_module_items, get_url



class Modules(Node):

    """
    This class is a container for all modules in a course.
    """

    def __init__(self, course_id, parent):

        super().__init__(parent, parent)
        self.course_id = course_id
        self.api_request = get_modules
        self.api_request_content = None
        self.get_all_items()

    @animate('Importing Modules')
    def get_all_items(self):

        api_request = self.api_request(self.course_id)
        if api_request:
            for module_dict in api_request:
                self.children.append(Module(self, self.parent, module_dict))



class Module(Node):

    """
    This class is a container for all module sections in a module.
    """

    def __init__(self, parent, root, api_dict, **kwargs):
        super().__init__(parent, root, api_dict['id'], api_dict['name'])
        self._expand_api_dict_to_class_attributes(api_dict)
        self.items_url = api_dict['items_url']
        self.url = root.course_url
        self.identify_content()

    def identify_content(self):
        from core.node_factory import get_node, get_content_node
        module_items = get_module_items(self.items_url)
        if module_items:
            for item in module_items:

                ResourceNode = get_node(item['type'])
                if ResourceNode:
                    module_item_dict = get_url(item['url'])
                    self.children.append(ResourceNode(self, self.root, module_item_dict))
                    continue

                if item.get('url'):
                    module_item_dict = get_url(item['url'])
                    if module_item_dict:
                        ContentNode = get_content_node(module_item_dict['url'], module_item_dict)
                        if ContentNode:
                            self.children.append(ContentNode(self, self.root, module_item_dict))

                if item.get('external_url'):
                    ContentNode = get_content_node(item['external_url'])
                    if ContentNode:
                        self.children.append(ContentNode(self, self.root, item, item['external_url'], item['title']))


