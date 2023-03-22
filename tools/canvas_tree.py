from treelib import Tree
import warnings

class CanvasTree:

    def __init__(self):
        self.tree = Tree()

    def init_node(self, root):
        self.tree.create_node(str(f"{root.title} | ID: {root.course_id}"), str(id(root)))

    def add_node(self, node):
        node_name = str(node)
        node_value = str(id(node))
        parent = str(id(node.parent))

        try:
            self.tree.create_node(node_name, node_value, parent)
        except:
            warnings.warn(f"Parent node {node.parent} is not in tree. {node} will not be visible")


    def show_nodes(self):
        return self.tree.show()