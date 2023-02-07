from base_node import Node
from network.api import get_module_items


class Module(Node):

    def __init__(self,  parent, api_dict):
        super().__init__(Node(parent))
        self.api_dict = api_dict
        self.get_module_items()
        self.name = api_dict['name']
        self.id = api_dict['id']
        self.get_module_items()


    def get_module_items(self):
        module_items = get_module_items(self.api_dict['items_url'])

        for item in module_items:

            if item.get("url"):

                self.url_list.append(item.get("url"))
            if item.get("external_url"):
                print(item['type'])
                self.url_list.append(item.get("external_url"))