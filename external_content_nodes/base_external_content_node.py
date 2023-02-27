

class BaseExternalNode:

    def __init__(self, parent, root, url, title=None, **kwargs):
        self.parent = parent
        self.root = root
        self.id = hash(url)
        self.url = url
        self.title = title
        self.children = []







