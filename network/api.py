import os
from os.path import join, dirname

import requests
import json

from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)


def response_handler(request_url):
    request = requests.get(request_url)

    return json.loads(request.content)


def get_announcements(course_id):

    announcement_url = f"{os.environ.get('api_path')}/announcements?context_codes=course_" \
                       f"{course_id}&access_token={os.environ.get('access_token')}"
    announcement_request = response_handler(announcement_url)
    return announcement_request


def get_assignments(course_id):
    assignment_url = f"{os.environ.get('api_path')}/courses/{course_id}" \
                     f"/assignments?access_token={os.environ.get('access_token')}"

    assignments_request = response_handler(assignment_url)
    return assignments_request


def get_discussions(course_id):
    discussions_url = f"{os.environ.get('api_path')}/courses/{course_id}" \
                      f"/discussion_topics?access_token={os.environ.get('access_token')}"
    discussions_request = response_handler(discussions_url)
    return discussions_request


def get_modules(course_id):
    modules_url = f"{os.environ.get('api_path')}/courses/{course_id}" \
                      f"/modules?access_token={os.environ.get('access_token')}"
    modules_request = response_handler(modules_url)
    return modules_request


def get_pages(course_id):
    pages_url = f"{os.environ.get('api_path')}/courses/{course_id}" \
                      f"/pages?access_token={os.environ.get('access_token')}"
    pages_request = response_handler(pages_url)
    return pages_request

def get_page(course_id, page_id):

    pages_url = f"{os.environ.get('api_path')}/courses/{course_id}" \
                f"/pages/{page_id}?access_token={os.environ.get('access_token')}"
    pages_request = response_handler(pages_url)
    return pages_request


def get_quizzes(course_id):
    quizzes_url = f"{os.environ.get('api_path')}/courses/{course_id}" \
                      f"/quizzes?access_token={os.environ.get('access_token')}"
    quizzes_request = response_handler(quizzes_url)
    return quizzes_request


def get_media_objects(course_id):
    media_objects_url = f"{os.environ.get('api_path')}/courses/{course_id}" \
                      f"/media_objects?access_token={os.environ.get('access_token')}"
    media_objects_request = response_handler(media_objects_url)
    return media_objects_request


def get_module_items(module_items_url):
    module_items_url = f"{module_items_url}?access_token={os.environ.get('access_token')}"
    media_objects_request = response_handler(module_items_url)
    return media_objects_request

