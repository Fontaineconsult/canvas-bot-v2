import os
from os.path import join, dirname

import requests
import json
import warnings
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)


def response_handler(request_url):
    request = requests.get(request_url)
    print("Calling", request_url)
    if request.status_code == 200:
        return json.loads(request.content)
    if request.status_code != 200:
        warning_message = f"{request.status_code} {json.loads(request.content)}"
        warnings.warn(warning_message, UserWarning)
        return None


def response_decorator(calling_function):
    def wrapper(*args):
        return response_handler(calling_function(*args))
    return wrapper

@response_decorator
def get_announcements(course_id):

    announcement_url = f"{os.environ.get('api_path')}/announcements?context_codes=course_" \
                       f"{course_id}&access_token={os.environ.get('access_token')}"
    return announcement_url

@response_decorator
def get_assignments(course_id):
    assignment_url = f"{os.environ.get('api_path')}/courses/{course_id}" \
                     f"/assignments?access_token={os.environ.get('access_token')}"

    return assignment_url


@response_decorator
def get_assignment(course_id, assignment_id):
    assignment_url = f"{os.environ.get('api_path')}/courses/{course_id}" \
                     f"/assignments/{assignment_id}?access_token={os.environ.get('access_token')}"
    return assignment_url



@response_decorator
def get_discussions(course_id):
    discussions_url = f"{os.environ.get('api_path')}/courses/{course_id}" \
                      f"/discussion_topics?access_token={os.environ.get('access_token')}"

    return discussions_url


@response_decorator
def get_discussion(course_id, topic_id):
    discussions_url = f"{os.environ.get('api_path')}/courses/{course_id}" \
                      f"/discussion_topics/{topic_id}?access_token={os.environ.get('access_token')}"

    return discussions_url

@response_decorator
def get_modules(course_id):
    modules_url = f"{os.environ.get('api_path')}/courses/{course_id}" \
                      f"/modules?access_token={os.environ.get('access_token')}"

    return modules_url

@response_decorator
def get_pages(course_id):
    pages_url = f"{os.environ.get('api_path')}/courses/{course_id}" \
                      f"/pages?access_token={os.environ.get('access_token')}"

    return pages_url
@response_decorator
def get_page(course_id, page_url):

    pages_url = f"{os.environ.get('api_path')}/courses/{course_id}" \
                f"/pages/{page_url}?access_token={os.environ.get('access_token')}"

    return pages_url

@response_decorator
def get_quizzes(course_id):
    quizzes_url = f"{os.environ.get('api_path')}/courses/{course_id}" \
                      f"/quizzes?access_token={os.environ.get('access_token')}"

    return quizzes_url


@response_decorator
def get_quiz(course_id, quiz_id):
    quizzes_url = f"{os.environ.get('api_path')}/courses/{course_id}" \
                  f"/quizzes/{quiz_id}?access_token={os.environ.get('access_token')}"
    return quizzes_url

@response_decorator
def get_media_objects(course_id):
    media_objects_url = f"{os.environ.get('api_path')}/courses/{course_id}" \
                      f"/media_objects?access_token={os.environ.get('access_token')}"

    return media_objects_url

@response_decorator
def get_module_items(module_items_url):
    module_items_url = f"{module_items_url}?access_token={os.environ.get('access_token')}"

    return module_items_url


@response_decorator
def get_url(url):
    authenticated_url = f"{url}?access_token={os.environ.get('access_token')}"
    return authenticated_url
