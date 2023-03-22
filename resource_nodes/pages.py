import animation

from network.api import get_pages, get_page
from resource_nodes.base_node import Node


class Pages(Node):


    def __init__(self, course_id, parent):

        super().__init__(parent, parent)
        self.course_id = course_id
        self.api_request = get_pages
        self.api_request_content = None
        self.get_all_items()

    @animation.wait('spinner')
    def get_all_items(self):

        api_request = self.api_request(self.course_id)
        if api_request:
            for module_dict in api_request:
                self.children.append(Page(self, self.parent, module_dict))



class Page(Node):

    def __init__(self, parent, root, api_dict, **kwargs):

        if not kwargs.get("bypass_get_url") is True:
            api_dict = get_page(root.course_id, api_dict['page_id'])

        if not api_dict.get('body'):
            api_dict = get_page(root.course_id, api_dict['page_id'])

        if api_dict:
            super().__init__(parent, root, api_dict['page_id'], api_dict['title'])
            self.root.manifest.add_item_to_manifest(self)
            self._expand_api_dict_to_class_attributes(api_dict)
            self.add_data_api_link_to_children(self.body)
            self.add_content_nodes_to_children(self.body)


