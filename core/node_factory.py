
from typing import Union, Type

from external_content_nodes.box import BoxPage
from resource_nodes.assignments import Assignment
from resource_nodes.announcements import Announcement
from resource_nodes.canvasfiles import CanvasFolder
from resource_nodes.discussions import Discussion
from resource_nodes.modules import Module
from resource_nodes.pages import Page
from resource_nodes.quizzes import Quiz
from sorters.sorters import resource_node_regex, document_content_regex, image_content_regex, web_video_content_regex, \
    video_file_content_regex, web_audio_content_regex, audio_file_content_regex, web_document_applications_regex, \
    file_storage_regex, ignore_list_regex, canvas_studio_embed, canvas_file_embed, canvas_media_embed
from resource_nodes.content_nodes import *


def get_node(type: str) -> Union[Type[Assignment],
                            Type[Page],
                            Type[Quiz],
                            Type[Announcement],
                            Type[Module],
                            Type[Discussion],
                            None]:

    node_dict = {
        "Assignment": Assignment,
        "Announcement": Announcement,
        "Discussion": Discussion,
        "Module": Module,
        "Page": Page,
        "Quiz": Quiz,

    }

    return node_dict.get(type)


def get_node_by_a_tag_match(a_tag: str, api_dict) -> Union[Type[Assignment],
                                        Type[Page],
                                        Type[Quiz],
                                        Type[Announcement],
                                        Type[Module],
                                        Type[Discussion],
                                        Type[Document],
                                        Type[DocumentSite],
                                        Type[VideoSite],
                                        Type[VideoFile],
                                        Type[AudioFile],
                                        Type[AudioSite],
                                        Type[ImageFile],
                                        Type[Unsorted],
                                        Type[FileStorageSite],
                                        None]:

    """
    A class factory that returns the appropriate class based on the a_tag
    :param a_tag:
    :param api_dict:
    :return:
    """


    match_link = resource_node_regex.search(a_tag)
    if match_link:
        node_dict = {
            "assignments": Assignment,
            "announcements": Announcement,
            "discussion_topics": Discussion,
            "modules": Module,
            "pages": Page,
            "quizzes": Quiz,
            "folders": CanvasFolder
        }

        if match_link.group() == 'files':
            return get_content_node(a_tag, api_dict)

        return node_dict[match_link.group()]



def get_content_node(content_url, api_dict=None, **kwargs) -> Union[Type[Document],
                                               Type[DocumentSite],
                                               Type[VideoSite],
                                               Type[VideoFile],
                                               Type[AudioFile],
                                               Type[AudioSite],
                                               Type[ImageFile],
                                               Type[Unsorted],
                                               Type[FileStorageSite],
                                               None]:


    """
    A class factory that returns the appropriate class based on the content_url
    :param content_url:
    :param api_dict:
    :param kwargs:
    :return:
    """

    if api_dict:
        content_url = api_dict['filename'] if api_dict.get('filename') else api_dict['title']

    if content_url is None:
        return None

    if ignore_list_regex.match(content_url):
        return None

    identified_content = identify_content_url(content_url, **kwargs)
    if identified_content:

        node_dict = {

            "document": Document,
            "documentSite": DocumentSite,
            "videoSite": VideoSite,
            "videoFile": VideoFile,
            "audioFile": AudioFile,
            "audioSite": AudioSite,
            "imageFile": ImageFile,
            "filestorage": BoxPage,
            "canvasStudioEmbed": CanvasStudioEmbed,
            "canvasFileEmbed": CanvasMediaEmbed,
            "canvasMediaEmbed": CanvasMediaEmbed,

        }

        return node_dict[identified_content]

    if not identified_content:
        return Unsorted




def identify_content_url(content_url, **kwargs) -> str:

    """
    A function that string matching the key in the class factories that matches the right content type
    :param content_url:
    :param kwargs:
    :return:
    """


    if document_content_regex.match(content_url):
        return "document"

    if image_content_regex.match(content_url):
        return "imageFile"

    if web_video_content_regex.match(content_url):
        return "videoSite"

    if video_file_content_regex.match(content_url):
        return "videoFile"

    if web_audio_content_regex.match(content_url):
        return "audioSite"

    if audio_file_content_regex.match(content_url):
        return "audioFile"

    if web_document_applications_regex.match(content_url):
        return "documentSite"

    if file_storage_regex.match(content_url):
        return "filestorage"

    if canvas_studio_embed.match(content_url):
        return "canvasStudioEmbed"

    if canvas_file_embed.match(content_url):
        return "canvasFileEmbed"

    if canvas_media_embed.match(content_url):
        return "canvasMediaEmbed"



