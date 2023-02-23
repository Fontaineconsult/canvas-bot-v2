
from typing import Union, Type
from resource_nodes.assignments import Assignment
from resource_nodes.announcements import Announcement
from resource_nodes.canvasfiles import CanvasFile
from resource_nodes.discussions import Discussion
from resource_nodes.modules import Module
from resource_nodes.pages import Page
from resource_nodes.quizzes import Quiz
from sorters.sorters import resource_node_regex
from network.api import *


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

    print(a_tag)
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
        }

        return node_dict[match_link.group()]



