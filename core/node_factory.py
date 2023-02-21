
from typing import Union, Type
from resource_nodes.assignments import Assignment
from resource_nodes.announcements import Announcement
from resource_nodes.discussions import Discussion
from resource_nodes.modules import Module
from resource_nodes.pages import Page
from resource_nodes.quizzes import Quiz

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


def get_endpoint(node):

    director_dict = {
        Assignment: get_assignment,
        Discussion: get_discussion,
        Module: get_module_items,
        Page: get_page,
        Quiz: get_quiz,

    }

    return director_dict.get(node)