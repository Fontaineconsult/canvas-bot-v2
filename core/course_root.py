import warnings
from os.path import join, dirname
from colorama import Fore, Style, init
from dotenv import load_dotenv
import os, sys
from core.content_extractor import ContentExtractor
from core.manifest import Manifest
from network.api import get_course
from resource_nodes.announcements import Announcements
from resource_nodes.assignments import Assignments
from resource_nodes.discussions import Discussions
from resource_nodes.canvasfiles import CanvasFiles
from resource_nodes.media_objects import CanvasMediaObjects
from resource_nodes.modules import Modules
from resource_nodes.pages import Pages
from resource_nodes.quizzes import Quizzes
from tools.canvas_tree import CanvasTree

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
init()


class CanvasCourseRoot(ContentExtractor):

    def __init__(self, course_id):

        self.course_id = course_id
        self.course_url = f"{os.environ.get('CANVAS_COURSE_PAGE_ROOT')}/{self.course_id}"
        self.canvas_tree = CanvasTree()
        self.manifest = Manifest()
        self.root_node = True
        self.title = None
        self.exists = False
        super().__init__(self.manifest, self.course_id, self.course_url, self.title, self.exists)

    def __str__(self):
        return f"<{Fore.GREEN}Canvas Course Root ID: {self.course_id} | {self.course_url}{Style.RESET_ALL}>"

    def initialize_course(self):
        course_api = get_course(self.course_id)
        if course_api:
            print(course_api)
            self.title = course_api['name'] # name used internally for course
            self.course_name = course_api['course_code'] # name used for course folder
            self.exists = True
            print(f"\nStarting import for {self.title} | {self.course_url}\n")
            self._init_modules_root()

        if not course_api:
            print(f"Course ID: {self.course_id} does not exist. Please check the course ID and try again.")

    def _init_modules_root(self):

        self.canvas_tree.init_node(self)

        self.modules = Modules(self.course_id, self)

        self.quizzes = Quizzes(self.course_id, self)

        self.assignments = Assignments(self.course_id, self)

        self.announcements = Announcements(self.course_id, self)

        self.discussions = Discussions(self.course_id, self)

        self.pages = Pages(self.course_id, self)

        self.files = CanvasFiles(self.course_id, self)

        self.media_objects = CanvasMediaObjects(self.course_id, self)
        print("Import Complete\n")
