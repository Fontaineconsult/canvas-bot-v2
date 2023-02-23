
from network.api import get_pages, get_page, get_url
from resource_nodes.base_node import Node
from tools.other_tools import get_content_id_key_from_api_url


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
        page_dict = get_page(root.course_id, api_dict['url'])
        super().__init__(parent, root, page_dict['page_id'], api_dict['title'])
        self.root.manifest.add_item_to_manifest(self)
        self._expand_api_dict_to_class_attributes(page_dict)
        self.add_data_api_link_to_children(self.body)
        print(self.get_html_body_links(self.body))
