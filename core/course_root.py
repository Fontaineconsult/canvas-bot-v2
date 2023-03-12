from os.path import join, dirname
from colorama import Fore, Style
from dotenv import load_dotenv
import animation, time
from core.content_extractor import ContentExtractor
from core.manifest import Manifest
from resource_nodes.announcements import Announcements
from resource_nodes.assignments import Assignments
from resource_nodes.discussions import Discussions
from resource_nodes.canvasfiles import CanvasFiles
from resource_nodes.media_objects import CanvasMediaObjects
from resource_nodes.modules import Modules
from resource_nodes.pages import Pages
from resource_nodes.quizzes import Quizzes
from tools.canvas_tree import CanvasTree

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)


class CanvasCourseRoot(ContentExtractor):

    def __init__(self, course_id):

        self.course_id = course_id
        self.canvas_tree = CanvasTree()
        self.manifest = Manifest()
        self._init_modules_root()
        self.root_node = True
        super().__init__(self.manifest)

    def __str__(self):
        return f"<{Fore.GREEN}Canvas Course Root ID: {self.course_id}{Style.RESET_ALL}>"

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




test = CanvasCourseRoot("12593")
test.canvas_tree.show_nodes()
print(test.build_documents_dict())
print(test.build_videos_dict())
print(test.build_audio_dict())
print(test.build_images_dict())

# for number in range(18158,19500):
#     test = CanvasCourseRoot(str(number))
#     test.canvas_tree.show_nodes()
#     test.manifest.print_manifest()
