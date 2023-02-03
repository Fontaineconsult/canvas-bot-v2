from os.path import join, dirname
from colorama import Fore, Style
from dotenv import load_dotenv

from resource_nodes.modules import Modules

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)


class CanvasCourseRoot:

    def __init__(self, course_id):
        self.course_id = course_id

    def __str__(self):
        return f"<{Fore.GREEN}Canvas Course Root ID: {self.course_id}{Style.RESET_ALL}>"


    def _init_modules_root(self):

        self.modules = Modules()