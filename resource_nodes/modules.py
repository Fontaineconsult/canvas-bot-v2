import os
from os.path import join, dirname
from colorama import Fore, Style
from dotenv import load_dotenv
import requests
import json



dotenv_path = join(dirname(__file__), '.env')
print(dotenv_path)
load_dotenv(r"C:\Users\DanielPC\Desktop\Servers\canvas-bot-v2\network\.env")

class Modules:

    def __init__(self, course_id):
        self.course_id = course_id
        self.api_url = f"{os.environ.get('api_path')}/{self.course_id}/modules?access_token={os.environ.get('access_token')}"
        self.api_request_content = None


    def get_modules_list(self):
        self.api_request_content = json.loads(requests.get(test.api_url).content)
















test = Modules('18411')
test.get_modules_list()

print(test.api_request_content)