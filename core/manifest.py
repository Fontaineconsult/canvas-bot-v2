from typing import Type, List, Union
from resource_nodes.base_content_node import BaseContentNode


class Manifest:

    """
    This class is used to store all of the nodes that are created during the course of the program.
    """

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


    def get_content_nodes(self, node_class_name):
        return [self.manifest[key][0] for key in self.keys() if self.manifest[key][0].__class__.__name__ == node_class_name]

    def content_summary(self) -> dict:
        """Return counts of all content items, broken down by class name and visibility."""
        from core.utilities import is_hidden
        nodes = self.content_list()
        by_class = {}
        hidden = 0
        for node in nodes:
            cls = node.__class__.__name__
            by_class[cls] = by_class.get(cls, 0) + 1
            if is_hidden(node):
                hidden += 1
        return {
            "total": len(nodes),
            "hidden": hidden,
            "by_class": by_class,
        }

    def resource_list(self) -> List:
        return [self.manifest[key][0] for key in self.keys() if not hasattr(self.manifest[key][0], "is_content")]

    def container_classes(self) -> set:
        """Return class names of resource nodes that are organizational containers (one per course)."""
        return {n.__class__.__name__ for n in self.resource_list() if getattr(n, 'is_container', False)}

    def resource_summary(self) -> dict:
        """Return counts of all resource items, broken down by class name and visibility."""
        from core.utilities import is_hidden
        nodes = self.resource_list()
        by_class = {}
        hidden = 0
        for node in nodes:
            cls = node.__class__.__name__
            by_class[cls] = by_class.get(cls, 0) + 1
            if is_hidden(node):
                hidden += 1
        return {
            "total": len(nodes),
            "hidden": hidden,
            "by_class": by_class,
        }