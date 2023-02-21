class BaseContentNode:

    def __init__(self, parent, root, info=None):
        self.info = info
        self.parent = parent
        self.root = root
        self.children = list()