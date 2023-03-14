from colorama import Fore, Style

from core.content_scaffolds import is_hidden
from resource_nodes.base_content_node import BaseContentNode



class Document(BaseContentNode):

    def __init__(self, parent, root, api_dict=None, url=None, title=None, **kwargs):
        super().__init__(parent, root, api_dict, url, title, **kwargs)

    def __str__(self):
        if self.parent.__class__.__name__ == 'BoxPage':
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {'Hidden' if is_hidden(self) else 'Visible'} {self.title}){Style.RESET_ALL}"
        else:
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {'Hidden' if is_hidden(self) else 'Visible'} {self.url}){Style.RESET_ALL}"


class DocumentSite(BaseContentNode):

    def __init__(self, parent, root, api_dict=None, url=None, title=None, **kwargs):
        super().__init__(parent, root, api_dict, url, title, **kwargs)


class VideoSite(BaseContentNode):


    def __init__(self, parent, root, api_dict=None, url=None, title=None, **kwargs):
        super().__init__(parent, root, api_dict, url, title, **kwargs)


class VideoFile(BaseContentNode):

    def __init__(self, parent, root, api_dict=None, url=None, title=None, **kwargs):
        super().__init__(parent, root, api_dict, url, title, **kwargs)

    def __str__(self):
        if self.parent.__class__.__name__ == 'BoxPage':
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {'Hidden' if is_hidden(self) else 'Visible'} {self.title}){Style.RESET_ALL}"
        else:
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {'Hidden' if is_hidden(self) else 'Visible'} {self.url}){Style.RESET_ALL}"


class AudioFile(BaseContentNode):

    def __init__(self, parent, root, api_dict=None, url=None, title=None, **kwargs):
        super().__init__(parent, root, api_dict, url, title, **kwargs)

    def __str__(self):
        if self.parent.__class__.__name__ == 'BoxPage':
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {'Hidden' if is_hidden(self) else 'Visible'} {self.title}){Style.RESET_ALL}"
        else:
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {'Hidden' if is_hidden(self) else 'Visible'} {self.url}){Style.RESET_ALL}"


class AudioSite(BaseContentNode):

    def __init__(self, parent, root, api_dict=None, url=None, title=None, **kwargs):
        super().__init__(parent, root, api_dict, url, title, **kwargs)


class ImageFile(BaseContentNode):

    def __init__(self, parent, root, api_dict=None, url=None, title=None, **kwargs):
        super().__init__(parent, root, api_dict, url, title, **kwargs)

    def __str__(self):
        if self.parent.__class__.__name__ == 'BoxPage':
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {'Hidden' if is_hidden(self) else 'Visible'} {self.title}){Style.RESET_ALL}"
        else:
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {'Hidden' if is_hidden(self) else 'Visible'} {self.url}){Style.RESET_ALL}"


class FileStorageSite(BaseContentNode):
    def __init__(self, parent, root, api_dict=None, url=None, title=None, **kwargs):
        super().__init__(parent, root, api_dict, url, title, **kwargs)



class DigitalTextbook(BaseContentNode):
    def __init__(self, parent, root, api_dict=None, url=None, title=None, **kwargs):
        super().__init__(parent, root, api_dict, url, title, **kwargs)


class Unsorted(BaseContentNode):

    def __init__(self, parent, root, api_dict=None, url=None, title=None, **kwargs):
        super().__init__(parent, root, api_dict, url, title, **kwargs)

    def __str__(self):
        if self.parent.__class__.__name__ == 'BoxPage':
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {'Hidden' if is_hidden(self) else 'Visible'} {self.title}){Style.RESET_ALL}"
        else:
            return f"{Fore.LIGHTWHITE_EX}({self.__class__.__name__} {'Hidden' if is_hidden(self) else 'Visible'} {self.url}){Style.RESET_ALL}"



