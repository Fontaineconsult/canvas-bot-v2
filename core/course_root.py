from colorama import Fore, Style, init
import os, sys, warnings
from core.content_extractor import ContentExtractor
from core.manifest import Manifest
from network.cred import set_canvas_studio_api_key_to_environment_variable
from resource_nodes.canvas_studio import CanvasStudio
from tools.canvas_tree import CanvasTree

from network.api import get_course, get_course_with_status, get_course_permissions
from resource_nodes.announcements import Announcements
from resource_nodes.assignments import Assignments
from resource_nodes.discussions import Discussions
from resource_nodes.canvasfiles import CanvasFiles
from resource_nodes.media_objects import CanvasMediaObjects
from resource_nodes.modules import Modules
from resource_nodes.pages import Pages
from resource_nodes.quizzes import Quizzes

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
init()  # colorama init


import logging
import tools.logger
log = logging.getLogger(__name__)



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

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            course_api, status, reason = get_course_with_status(self.course_id)

        if course_api:
            log.info(f"Course API: {self.course_id} Exists")
            self.title = course_api['name'] # name used internally for course
            self.course_name = course_api['course_code'] # name used for course folder
            self.exists = True
            print(f"\nStarting import for {self.title} | {self.course_url}\n")
            log.info(f"AUDIT: Course scan start | course_id={self.course_id} | title={self.title} | url={self.course_url}")
            if not self._print_permission_summary():
                return
            self._init_modules_root()
            return

        log.warning(f"Course API: {self.course_id} | status={status} | reason={reason}")
        api_path = os.environ.get('API_PATH', '[unknown]')
        print(f"\n{Fore.RED}[ERROR] Could not load Course {self.course_id}{Style.RESET_ALL}")
        print(f"  {'Canvas API URL:':<18} {api_path}")
        if status is None:
            print(f"  {'Network error:':<18} {reason}")
            print(f"  Could not reach Canvas. Check your network connection.\n")
            return
        print(f"  {'HTTP response:':<18} {status} {reason}")

        if status == 404 and reason == "course_not_found":
            explanation = "Course not found at this Canvas URL."
        elif status == 404 and reason == "api_path_invalid":
            explanation = "Canvas didn't recognize this URL. Run --reset_canvas_params to re-enter your Canvas subdomain."
        elif status == 401:
            explanation = "API token rejected. Run --reset_canvas_params to enter a fresh token."
        elif status == 403:
            explanation = "Token works, but your account doesn't have permission to view this course."
        else:
            explanation = "Unexpected response from Canvas. Check the log for details."
        print(f"  {explanation}\n")

    def _print_permission_summary(self):
        """Surface the Canvas course permissions Canvas Bot relies on (read + file edit).

        Returns True if the scan should continue, False if the user lacks read access.
        """
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            perms = get_course_permissions(self.course_id)

        if not perms:
            print(f"{Fore.YELLOW}Permissions: could not retrieve{Style.RESET_ALL}\n")
            log.info(f"AUDIT: Permissions | course_id={self.course_id} | retrieval_failed")
            return True  # can't tell — give benefit of the doubt and let the scan try

        can_read = bool(perms.get("read_as_admin") or perms.get("read_as_member"))
        can_view_hidden = bool(perms.get("view_unpublished_items"))
        can_edit_files = bool(perms.get("manage_files_edit"))

        def mark(flag):
            return f"{Fore.GREEN}OK{Style.RESET_ALL}" if flag else f"{Fore.RED}NO{Style.RESET_ALL}"

        print(f"Permissions: Read {mark(can_read)} | View Unpublished {mark(can_view_hidden)} | Edit Files {mark(can_edit_files)}\n")
        log.info(
            f"AUDIT: Permissions | course_id={self.course_id} "
            f"| read={can_read} | view_unpublished={can_view_hidden} | edit_files={can_edit_files}"
        )

        if not can_read:
            print(f"{Fore.RED}[ERROR] No read access to this course. Scan cannot continue.{Style.RESET_ALL}")
            print(f"  Your Canvas token has no read permission for course {self.course_id}.\n")
            log.warning(f"AUDIT: Scan halted | course_id={self.course_id} | reason=no_read_access")
            return False
        return True

    def _init_modules_root(self):

        self.canvas_tree.init_node(self)

        if os.environ.get('studio_enabled') != 'True':
            print("Canvas Studio is not enabled. Skipping Canvas Studio Import")
        elif not set_canvas_studio_api_key_to_environment_variable():
            print("Canvas Studio is enabled but credentials could not be loaded. Skipping Canvas Studio Import")
        else:
            self.canvas_studio = CanvasStudio(self.course_id, self)

        self.modules = Modules(self.course_id, self)

        self.quizzes = Quizzes(self.course_id, self)

        self.assignments = Assignments(self.course_id, self)

        self.announcements = Announcements(self.course_id, self)

        self.discussions = Discussions(self.course_id, self)

        self.pages = Pages(self.course_id, self)

        self.files = CanvasFiles(self.course_id, self)

        self.media_objects = CanvasMediaObjects(self.course_id, self)


        from tools.warning_collector import get_collector
        get_collector().flush()

        log.info(f"AUDIT: Course scan complete | course_id={self.course_id} | items={len(self.manifest.content_list())}")
        print("Import Complete\n")
