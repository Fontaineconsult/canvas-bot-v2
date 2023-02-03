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

    def __init__(self, course_id, parent):
        self.parent = parent
        self.children = []
        self.course_id = course_id
        self.api_url = f"{os.environ.get('api_path')}/{self.course_id}/modules?access_token={os.environ.get('access_token')}"
        self.api_request_content = None
        self.get_modules_list()
        self.sort_children()

    def get_modules_list(self):
        self.api_request_content = json.loads(requests.get(self.api_url).content)


    def sort_children(self):
        for each in self.api_request_content:
            print(each['items_url'])
            string = f"{each['items_url']}?access_token={os.environ.get('access_token')}?per_page=20"
            print(string)
            items = requests.get(f"{each['items_url']}?access_token={os.environ.get('access_token')}&per_page=100")
            # print(json.loads(items.content))
            for item in json.loads(items.content):
                print(item)














test = Modules('18411', "fgef")
