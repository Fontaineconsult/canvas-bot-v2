from colorama import Fore, Style


from network.api import get_discussions, get_files, get_file, get_url
from resource_nodes.base_content_node import BaseCanvasContentNode
from resource_nodes.base_node import Node



def canvas_file_factory(node):
    from core.node_factory import get_content_node
    print(vars(node))
    print(get_content_node(node.filename))

    return CanvasFile


class CanvasFiles(Node):

    def __init__(self, course_id, parent):

        super().__init__(parent, parent)
        self.course_id = course_id
        self.api_request = get_files
        self.get_all_items()

    def get_all_items(self):

        api_request = self.api_request(self.course_id)
        if api_request:
            for file_dict in api_request:
                self.children.append(CanvasFile(self, self.parent, file_dict))


class CanvasFile(BaseCanvasContentNode):

    def __init__(self, parent, root, api_dict, **kwargs):

        if not kwargs.get("bypass_get_url") is True:
            api_dict = get_file(root.course_id, api_dict['id'])
        super().__init__(parent, root, api_dict['id'], api_dict['filename'])


        self.root.manifest.add_item_to_manifest(self)
        self._expand_api_dict_to_class_attributes(api_dict)


class CanvasFolder(Node):

    def __init__(self, parent, root, api_dict, **kwargs):

        super().__init__(parent, root, api_dict['id'], api_dict['full_name'])
        self.root.manifest.add_item_to_manifest(self)
        self._expand_api_dict_to_class_attributes(api_dict)
        self.get_all_items()


    def get_all_items(self):

        canvas_folder_contents = get_url(self.files_url)
        if canvas_folder_contents:
            for file_dict in canvas_folder_contents:
                self.children.append(CanvasFile(self, self.root, file_dict))