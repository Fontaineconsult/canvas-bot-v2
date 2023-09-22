from colorama import Fore, Style, init

from core.content_scaffolds import is_hidden
from resource_nodes.base_content_node import BaseContentNode
from tools.string_checking.url_cleaning import is_url, sanitize_windows_filename

init()


def hidden():
    return f"{Fore.RED} Hidden {Style.RESET_ALL}"


def visible():
    return f"{Fore.LIGHTGREEN_EX} Visible {Style.RESET_ALL}"


def captioned():
    return f"{Fore.LIGHTGREEN_EX} Captioned {Style.RESET_ALL}"


def not_captioned():
    return f"{Fore.RED} Not Captioned {Style.RESET_ALL}"

class Document(BaseContentNode):

    def __init__(self, parent, root, api_dict=None, url=None, title=None, **kwargs):
        if api_dict is None and is_url(title) is True:
            title = sanitize_windows_filename(url.split('/')[-1])
        super().__init__(parent, root, api_dict, url, title, **kwargs)

    def __str__(self):
        if self.parent.__class__.__name__ == 'BoxPage':
            return f"{Fore.LIGHTCYAN_EX}( {self.__class__.__name__}{Style.RESET_ALL}{Fore.LIGHTWHITE_EX} {hidden() if is_hidden(self) else visible()} {self.title} ){Style.RESET_ALL}"
        else:
            return f"{Fore.LIGHTCYAN_EX}( {self.__class__.__name__}{Style.RESET_ALL}{Fore.LIGHTWHITE_EX} {hidden() if is_hidden(self) else visible()} {self.url} ){Style.RESET_ALL}"


class DocumentSite(BaseContentNode):

    def __init__(self, parent, root, api_dict=None, url=None, title=None, **kwargs):
        super().__init__(parent, root, api_dict, url, title, **kwargs)


class VideoSite(BaseContentNode):

    def __init__(self, parent, root, api_dict=None, url=None, title=None, captioned=False, **kwargs):
        super().__init__(parent, root, api_dict, url, title, captioned, **kwargs)
        self.captioned = False

    def __str__(self):
        return f"{Fore.LIGHTRED_EX}( {self.__class__.__name__}{Style.RESET_ALL}{Fore.LIGHTWHITE_EX} {hidden() if is_hidden(self) else visible()} {captioned() if self.captioned else not_captioned()} {self.url}  ){Style.RESET_ALL}"


class VideoFile(BaseContentNode):

    def __init__(self, parent, root, api_dict=None, url=None, title=None, captioned=False, **kwargs):

        if api_dict is None and is_url(title) is True:
            title = sanitize_windows_filename(url.split('/')[-1])
        super().__init__(parent, root, api_dict, url, title, captioned,  **kwargs)


    def __str__(self):
        if self.parent.__class__.__name__ == 'BoxPage':
            return f"{Fore.LIGHTMAGENTA_EX}( {self.__class__.__name__}{Style.RESET_ALL}{Fore.LIGHTWHITE_EX} {hidden() if is_hidden(self) else visible()} {self.title} ){Style.RESET_ALL}"
        else:
            return f"{Fore.LIGHTMAGENTA_EX}( {self.__class__.__name__}{Style.RESET_ALL}{Fore.LIGHTWHITE_EX} {hidden() if is_hidden(self) else visible()} {captioned() if self.captioned else not_captioned()} {self.url} ){Style.RESET_ALL}"


class AudioFile(BaseContentNode):

    def __init__(self, parent, root, api_dict=None, url=None, title=None, captioned=False, **kwargs):

        if api_dict is None and is_url(title) is True:
            title = sanitize_windows_filename(url.split('/')[-1])
        super().__init__(parent, root, api_dict, url, title, captioned, **kwargs)

    def __str__(self):
        if self.parent.__class__.__name__ == 'BoxPage':
            return f"{Fore.LIGHTGREEN_EX}( {self.__class__.__name__} {hidden() if is_hidden(self) else visible()} {self.title} ){Style.RESET_ALL}"
        else:
            return f"{Fore.LIGHTGREEN_EX}( {self.__class__.__name__} {hidden() if is_hidden(self) else visible()} {self.url} ){Style.RESET_ALL}"


class AudioSite(BaseContentNode):

    def __init__(self, parent, root, api_dict=None, url=None, title=None, **kwargs):
        super().__init__(parent, root, api_dict, url, title, **kwargs)


class ImageFile(BaseContentNode):

    def __init__(self, parent, root, api_dict=None, url=None, title=None, **kwargs):
        if api_dict is None and title is None:
            title = sanitize_windows_filename(url.split('/')[-1])

        super().__init__(parent, root, api_dict, url, title, **kwargs)

    def __str__(self):
        if self.parent.__class__.__name__ == 'BoxPage':
            return f"{Fore.LIGHTYELLOW_EX}( {self.__class__.__name__} {hidden() if is_hidden(self) else visible()} {self.title} ){Style.RESET_ALL}"
        else:
            return f"{Fore.LIGHTYELLOW_EX}( {self.__class__.__name__} {hidden() if is_hidden(self) else visible()} {self.url} ){Style.RESET_ALL}"


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
            return f"{Fore.LIGHTWHITE_EX}( {self.__class__.__name__} {hidden() if is_hidden(self) else visible()} {self.title} ){Style.RESET_ALL}"
        else:
            return f"{Fore.LIGHTWHITE_EX}( {self.__class__.__name__} {hidden() if is_hidden(self) else visible()} {self.url} ){Style.RESET_ALL}"



