from colorama import Fore, Style

from resource_nodes.base_content_node import BaseContentNode







class Document(BaseContentNode):

    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)


    def __str__(self):
        if self.parent.__class__.__name__ == 'BoxPage':
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {self.title}){Style.RESET_ALL}"
        else:
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {self.url}){Style.RESET_ALL}"




class DocumentSite(BaseContentNode):

    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)


class VideoSite(BaseContentNode):


    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)


class VideoFile(BaseContentNode):

    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)

    def __str__(self):
        if self.parent.__class__.__name__ == 'BoxPage':
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {self.title}){Style.RESET_ALL}"
        else:
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {self.url}){Style.RESET_ALL}"


class AudioFile(BaseContentNode):

    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)

    def __str__(self):
        if self.parent.__class__.__name__ == 'BoxPage':
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {self.title}){Style.RESET_ALL}"
        else:
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {self.url}){Style.RESET_ALL}"


class AudioSite(BaseContentNode):

    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)


class ImageFile(BaseContentNode):

    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)

    def __str__(self):
        if self.parent.__class__.__name__ == 'BoxPage':
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {self.title}){Style.RESET_ALL}"
        else:
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {self.url}){Style.RESET_ALL}"


class FileStorageSite(BaseContentNode):
    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)



class DigitalTextbook(BaseContentNode):
    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)



class Unsorted(BaseContentNode):

    def __init__(self, parent, root, url, title):
        super().__init__(parent, root, url, title)

    def __str__(self):
        if self.parent.__class__.__name__ == 'BoxPage':
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {self.title}){Style.RESET_ALL}"
        else:
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {self.url}){Style.RESET_ALL}"



