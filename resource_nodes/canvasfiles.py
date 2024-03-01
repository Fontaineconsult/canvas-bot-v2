from network.api import get_files, get_url
from resource_nodes.base_node import Node
from tools.animation import animate


class CanvasFiles(Node):

    """
    The CanvasFiles class is a container for files stored directly in the Canvas LMS. CanvasFile nodes are re-classed as
    content nodes based on their API data before adding to the tree.
    """

    def __init__(self, course_id, parent):

        super().__init__(parent, parent)
        self.course_id = course_id
        self.api_request = get_files
        self.get_all_items()

    @animate('Importing Canvas Files')
    def get_all_items(self):
        from core.node_factory import get_content_node
        api_request = self.api_request(self.course_id)

        if api_request:
            for file_dict in api_request:
                if not self.root.manifest.id_exists(file_dict['id']):
                    content_node = get_content_node(None, file_dict)
                    if content_node:
                        self.children.append(content_node(self, self.parent, file_dict))


class CanvasFolder(Node):

    def __init__(self, parent, root, api_dict, **kwargs):

        super().__init__(parent, root, api_dict['id'], api_dict['full_name'])
        self.root.manifest.add_item_to_manifest(self)
        self._expand_api_dict_to_class_attributes(api_dict)
        self.get_all_items()


    def get_all_items(self):
        from core.node_factory import get_content_node
        canvas_folder_contents = get_url(self.files_url)
        if canvas_folder_contents:
            for file_dict in canvas_folder_contents:
                content_node = get_content_node(None, file_dict)
                if content_node:
                    self.children.append(content_node(self, self.root, file_dict))