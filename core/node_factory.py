from resource_nodes.assignments import Assignment
from resource_nodes.announcements import Announcement
from resource_nodes.discussions import Discussion
from resource_nodes.modules import Module
from resource_nodes.pages import Page
from resource_nodes.quizzes import Quiz

def get_node(type):

    node_dict = {
        "Assignment": Assignment,
        "Announcements": Announcement,
        "Discussion": Discussion,
        "Module": Module,
        "Page": Page,
        "Quiz": Quiz
    }

    return node_dict[type]

