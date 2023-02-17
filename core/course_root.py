from os.path import join, dirname
from colorama import Fore, Style
from dotenv import load_dotenv

from resource_nodes.announcements import Announcements
from resource_nodes.assignments import Assignments
from resource_nodes.discussions import Discussions
from resource_nodes.modules import Modules
from resource_nodes.pages import Pages
from resource_nodes.quizzes import Quizzes
from tools.canvas_tree import CanvasTree

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)


class CanvasCourseRoot:

    def __init__(self, course_id):
        self.course_id = course_id
        self.canvas_tree = CanvasTree()
        self._init_modules_root()


    def __str__(self):
        return f"<{Fore.GREEN}Canvas Course Root ID: {self.course_id}{Style.RESET_ALL}>"


    def _init_modules_root(self):
        self.canvas_tree.init_node(self)

        self.assignments = Assignments(self.course_id, self)
        self.announcements = Announcements(self.course_id, self)
        self.modules = Modules(self.course_id, self)
        self.discussions = Discussions(self.course_id, self)
        self.pages = Pages(self.course_id, self)
        self.quizzes = Quizzes(self.course_id, self)



test = CanvasCourseRoot("18411")
test.canvas_tree.show_nodes()