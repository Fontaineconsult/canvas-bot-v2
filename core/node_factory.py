
from typing import Union, Type
from resource_nodes.assignments import Assignment
from resource_nodes.announcements import Announcement
from resource_nodes.canvasfiles import CanvasFile, CanvasFolder
from resource_nodes.discussions import Discussion
from resource_nodes.modules import Module
from resource_nodes.pages import Page
from resource_nodes.quizzes import Quiz
from sorters.sorters import resource_node_regex, document_content_regex, image_content_regex, web_video_content_regex, \
    video_file_content_regex, web_audio_content_regex, audio_file_content_regex, web_document_applications_regex, \
    file_storage_regex
from network.api import *
from resource_nodes.content_nodes import *

def get_node(type) -> Union[Type[Assignment],
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


def get_node_by_a_tag_match(a_tag) -> Union[Type[Assignment],
                                        Type[Page],
                                        Type[Quiz],
                                        Type[Announcement],
                                        Type[Module],
                                        Type[Discussion],
                                        Type[CanvasFile],
                                        None]:


    match_link = resource_node_regex.search(a_tag)

    if match_link:
        node_dict = {
            "assignments": Assignment,
            "announcements": Announcement,
            "discussion_topics": Discussion,
            "modules": Module,
            "pages": Page,
            "quizzes": Quiz,
            "files": CanvasFile,
            "folders": CanvasFolder
        }

        return node_dict[match_link.group()]



def get_content_node(content_url, **kwargs) -> Union[Type[Document],
                                               Type[DocumentSite],
                                               Type[VideoSite],
                                               Type[VideoFile],
                                               Type[AudioFile],
                                               Type[AudioSite],
                                               Type[ImageFile],
                                               Type[Unsorted],
                                               Type[FileStorageSite],
                                               None]:

    identified_content = identify_content_url(content_url, **kwargs)

    if identified_content:

        node_dict = {

            "document": Document,
            "documentSite": DocumentSite,
            "videoSite": VideoSite,
            "videoFile": VideoFile,
            "audioFile": AudioFile,
            "audioFite": AudioSite,
            "imageFile": ImageFile,
            "filestorage": FileStorageSite,

        }

        return node_dict[identified_content]

    if not identified_content:
        return Unsorted



def identify_content_url(content_url, **kwargs) -> str:



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

