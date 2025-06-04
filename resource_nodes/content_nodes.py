import re

from colorama import Fore, Style, init

from core.content_scaffolds import is_hidden
from network.api import get_file, get_media_object, get_media_objects
from network.studio_api import get_media_by_id, get_media_sources_by_id, get_media_perspectives_by_id, \
    get_captions_by_media_id
from resource_nodes.base_content_node import BaseContentNode
from sorters.sorters import canvas_file_embed, canvas_media_embed
from tools.string_checking.url_cleaning import is_url, sanitize_windows_filename

from config.yaml_io import read_re

expressions = read_re()


init()  # colorama


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
            return f"{Fore.LIGHTMAGENTA_EX}( {self.__class__.__name__}{Style.RESET_ALL}{Fore.LIGHTWHITE_EX} {hidden() if is_hidden(self) else visible()} {captioned() if self.captioned else not_captioned()} {self.title} {self.url} ){Style.RESET_ALL}"


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


class CanvasMediaEmbed(BaseContentNode):
    def __init__(self, parent, root, api_dict=None, url=None, title=None, **kwargs):

        id = None
        download_url = None
        file_name = None

        if canvas_file_embed.match(url) is not None:
            pattern = canvas_file_embed.match(url).group(1)

            file_dict = get_file(root.course_id ,pattern)
            if file_dict:
                id = file_dict['media_entry_id']
                api_dict = file_dict
                download_url = file_dict['url']
                file_name = file_dict['filename']

        if canvas_media_embed.match(url) is not None:

            pattern = canvas_media_embed.match(url).group(1)
            media_objects = get_media_objects(root.course_id)

            if media_objects:

                for media_object in media_objects:
                    if media_object['media_id'] == f"m-{pattern}":

                        id = media_object['media_id']
                        api_dict = media_object
                        file_name = media_object['title']
                        download_url = media_object["media_sources"][0]['url']


        super().__init__(parent, root, api_dict, url, title, **kwargs)

        if id:
            self.id = id
        if download_url:
            self.download_url = download_url
        if file_name:
            self.file_name = file_name


    def __str__(self):
        return f"{Fore.LIGHTRED_EX}( {self.__class__.__name__}{Style.RESET_ALL}{Fore.LIGHTWHITE_EX} {hidden() if is_hidden(self) else visible()} {captioned() if self.captioned else not_captioned()} {self.title} {self.url}  ){Style.RESET_ALL}"

class CanvasStudioEmbed(BaseContentNode):

    def __init__(self, parent, root, api_dict=None, url=None, title=None, **kwargs):
        if api_dict:
            canvas_studio_id = re.search(re.compile(expressions['canvas_embed_uuid_regex'][0]), api_dict['external_url']).group(2)

        else:
            canvas_studio_id = re.search(re.compile(expressions['canvas_embed_uuid_regex'][0]), url).group(2)

        super().__init__(parent, root, api_dict, url, title, **kwargs)
        self.id = canvas_studio_id
        media = get_media_by_id(canvas_studio_id)
        try:
            self.title = media['media']['title']
        except TypeError:
            self.title = None
        media_source = get_media_sources_by_id(self.id)
        captions = get_captions_by_media_id(self.id)

        if captions is not None and len(captions['caption_files']) > 0:
            self.captioned = True
            self.captions_list = captions['caption_files']
        if media_source:
            for source in media_source['sources']:

                if source.get('definition') == "low": # we just want the smallest file size
                    self.download_url = source['url']
                    self.mime_type = source['mime_type']
                else:
                    self.download_url = media_source['sources'][0]["url"]
                    self.mime_type = media_source['sources'][0]['mime_type']

        self.is_canvas_studio_file = True

    def __str__(self):
        return f"{Fore.LIGHTRED_EX}( {self.__class__.__name__}{Style.RESET_ALL}{Fore.LIGHTWHITE_EX} {hidden() if is_hidden(self) else visible()} {captioned() if self.captioned else not_captioned()} {self.title} {self.url}  ){Style.RESET_ALL}"