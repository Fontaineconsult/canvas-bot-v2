from typing import Type, List, Union
from resource_nodes.base_content_node import BaseContentNode


class Manifest:

    def __init__(self):
        self.manifest = dict()

    def add_item_to_manifest(self, node):
        if not self.get_item_from_manifest(node.item_id):
            self.manifest[node.item_id] = [node]
        else:
            self.manifest[node.item_id].append(node)

    def get_item_from_manifest(self, node_id):
        node = self.manifest.get(node_id)
        if node is not None:
            return self.manifest[node_id][0]

    def keys(self):
        return self.manifest.keys()

    def node_exists(self, node) -> bool:
        if node.item_id in self.manifest.keys():
            return True
        return False

    def content_list(self) -> List[Union[Type[BaseContentNode]]]:
        return [self.manifest[key][0] for key in self.keys() if hasattr(self.manifest[key][0], "is_content")]

    def id_exists(self, item_id) -> bool:
        if item_id in self.manifest.keys():
            return True
        return False

    def print_manifest(self):
        for item in self.manifest:
            print(item, self.manifest[item])

