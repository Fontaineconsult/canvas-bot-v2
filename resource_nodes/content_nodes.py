from resource_nodes.base_content_node import BaseContentNode


class Document(BaseContentNode):

    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)


class DocumentSite(BaseContentNode):

    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)


class VideoSite(BaseContentNode):


    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)


class VideoFile(BaseContentNode):

    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)


class AudioFile(BaseContentNode):

    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)


class AudioSite(BaseContentNode):

    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)


class ImageFile(BaseContentNode):

    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)


class FileStorageSite(BaseContentNode):
    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)


class DigitalTextbook(BaseContentNode):
    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)



class Unsorted(BaseContentNode):

    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)
