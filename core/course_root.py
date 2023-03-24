import warnings
from os.path import join, dirname
from colorama import Fore, Style
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

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)


class CanvasCourseRoot(ContentExtractor):

    def __init__(self, course_id):

        self.detect_and_set_env_file()
        self.course_id = course_id
        self.course_url = f"{os.environ.get('canvas_course_page_root')}/{self.course_id}"
        self.canvas_tree = CanvasTree()
        self.manifest = Manifest()
        self.root_node = True
        self.title = None
        super().__init__(self.manifest, self.course_id, self.course_url, self.title)


    def __str__(self):
        return f"<{Fore.GREEN}Canvas Course Root ID: {self.course_id} | {self.course_url}{Style.RESET_ALL}>"

    def detect_and_set_env_file(self):
        pass

    def initialize_course(self):
        course_api = get_course(self.course_id)
        if course_api:
            self.title = course_api['name']
            print(f"\nStarting import for {self.title} | {self.course_url}\n")
            self._init_modules_root()

        if not course_api:
            print(f"Course ID: {self.course_id} does not exist. Please check the course ID and try again.")


    def _init_modules_root(self):

        self.canvas_tree.init_node(self)

        print("Importing Modules")
        self.modules = Modules(self.course_id, self)

        print("Importing Assignments")
        self.assignments = Assignments(self.course_id, self)

        print("Importing Announcements")
        self.announcements = Announcements(self.course_id, self)

        print("Importing Discussions")
        self.discussions = Discussions(self.course_id, self)

        print("Importing Pages")
        self.pages = Pages(self.course_id, self)

        print("Importing Quizzes")
        self.quizzes = Quizzes(self.course_id, self)

        print("Importing Canvas Files")
        self.files = CanvasFiles(self.course_id, self)

        print("Importing Media Objects")
        self.media_objects = CanvasMediaObjects(self.course_id, self)
        print("Import Complete")
