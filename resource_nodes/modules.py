
from base_node import Node
from network.api import get_modules, get_module_items



class Modules(Node):

    def __init__(self, course_id, parent):
        super().__init__(Node(parent))
        self.course_id = course_id
        self.api_request = get_modules
        self.api_request_content = None
        self.get_all_items()

    def get_all_items(self):
        api_request = self.api_request(self.course_id)
        print(api_request)


        for each in api_request:
            print("MOD", each)

            module_items = get_module_items(each['items_url'])

            for item in module_items:
                print(item)










test = Modules('18411', "fgef")
