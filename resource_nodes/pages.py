from network.api import get_pages
from resource_nodes.base_node import Node


class Pages(Node):


    def __init__(self, course_id, parent):

        super().__init__(parent, parent)
        self.course_id = course_id
        self.api_request = get_pages
        self.api_request_content = None
        self.get_all_items()

    def get_all_items(self):

        api_request = self.api_request(self.course_id)

        for module_dict in api_request:
            self.children.append(Page(self, self.parent, module_dict))



class Page(Node):

    def __init__(self, parent, root, api_dict):

        super().__init__(parent, root, api_dict['page_id'], api_dict['title'])
        self.api_dict = api_dict
        self.content_url = self.api_dict['html_url']
        self.root.manifest.add_item_to_manifest(self)