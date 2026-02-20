import os
import logging

import requests
from requests.exceptions import MissingSchema
import json
import warnings

from network.cred import set_canvas_api_key_to_environment_variable, load_config_data_from_appdata

log = logging.getLogger(__name__)



if __name__=="__main__":
    set_canvas_api_key_to_environment_variable()
    load_config_data_from_appdata()


def _clean_url(url):
    """Strip access_token from URL for safe display."""
    if 'access_token=' in url:
        url = url.split('access_token=')[0].rstrip('?&')
    return url


def _extract_error_message(error_data):
    """Extract human-readable message from Canvas API error response."""
    if isinstance(error_data, dict):
        # Canvas format: {'errors': [{'message': '...'}], 'status': '...'}
        errors = error_data.get('errors', [])
        if errors and isinstance(errors[0], dict):
            return errors[0].get('message', error_data.get('status', str(error_data)))
        return error_data.get('status', error_data.get('message', str(error_data)))
    return str(error_data)


def response_handler(request_url):
    clean_url = _clean_url(request_url)
    try:
        # Perform the GET request
        request = requests.get(request_url, verify=True)
    except ConnectionError as exc:
        # Log and warn for connection errors
        log.exception(f"Connection error occurred: {exc} | URL: {clean_url}")
        warnings.warn(f"Connection error\n    {clean_url}", UserWarning)
        return False
    except MissingSchema as exc:
        # Log and warn for invalid URL schema
        log.exception(f"Invalid URL schema: {exc} | URL: {clean_url}")
        warnings.warn(f"Invalid URL\n    {clean_url}", UserWarning)
        return None

    # Handle HTTP responses
    if request.status_code == 200:
        log.info(f"Request successful: {clean_url} | Status Code: {request.status_code}")
        try:
            return json.loads(request.content)
        except json.JSONDecodeError as exc:
            log.exception(f"Failed to decode JSON: {exc} | URL: {clean_url}")
            warnings.warn(f"Invalid JSON response\n    {clean_url}", UserWarning)
            return None
    else:
        log.warning(f"Request failed: {clean_url} | Status Code: {request.status_code}")
        try:
            error_data = json.loads(request.content)
            error_message = _extract_error_message(error_data)
        except json.JSONDecodeError as exc:
            log.exception(f"Failed to decode error JSON: {exc} | URL: {clean_url}")
            error_message = "Failed to parse error response"
        warnings.warn(f"HTTP {request.status_code} - {error_message}\n    {clean_url}", UserWarning)
        return None


def response_decorator(calling_function):
    def wrapper(*args):
        return response_handler(calling_function(*args))
    return wrapper



@response_decorator
def get_active_accounts(page):
    active_account_url = f"{os.environ.get('API_PATH')}/accounts/1/courses?page={page}&per_page=100&access_token={os.environ.get('access_token')}"
    return active_account_url



@response_decorator
def get_course(course_id):
    course_url = f"{os.environ.get('API_PATH')}/courses/{course_id}?access_token={os.environ.get('access_token')}"
    return course_url


@response_decorator
def get_users_in_account(account_id):
    course_url = f"{os.environ.get('API_PATH')}/accounts/{account_id}/users?access_token={os.environ.get('access_token')}"
    return course_url


@response_decorator
def get_users_scope(account_id):
    course_url = f"{os.environ.get('API_PATH')}/accounts/self/scopes?access_token={os.environ.get('access_token')}"
    return course_url



@response_decorator
def get_announcements(course_id):

    announcement_url = f"{os.environ.get('API_PATH')}/announcements?context_codes=course_" \
                       f"{course_id}&access_token={os.environ.get('access_token')}&per_page=100"
    return announcement_url


@response_decorator
def get_assignments(course_id):
    assignments_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                     f"/assignments?access_token={os.environ.get('access_token')}&per_page=100"
    return assignments_url


@response_decorator
def get_assignment(course_id, assignment_id):
    assignment_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                     f"/assignments/{assignment_id}?access_token={os.environ.get('access_token')}"
    return assignment_url


@response_decorator
def get_discussions(course_id):
    discussions_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                      f"/discussion_topics?access_token={os.environ.get('access_token')}&per_page=100"

    return discussions_url


@response_decorator
def get_discussion(course_id, topic_id):
    discussions_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                      f"/discussion_topics/{topic_id}?access_token={os.environ.get('access_token')}"

    return discussions_url

@response_decorator
def get_modules(course_id):
    modules_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                      f"/modules?access_token={os.environ.get('access_token')}&per_page=100"

    return modules_url


@response_decorator
def get_pages(course_id):
    pages_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                      f"/pages?access_token={os.environ.get('access_token')}&per_page=100"

    return pages_url

@response_decorator
def get_page(course_id, page_url):

    page_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                f"/pages/{page_url}?access_token={os.environ.get('access_token')}"

    return page_url


@response_decorator
def get_quizzes(course_id):
    quizzes_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                      f"/quizzes?access_token={os.environ.get('access_token')}&per_page=100"
    return quizzes_url


@response_decorator
def get_quiz(course_id, quiz_id):
    quizzes_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                  f"/quizzes/{quiz_id}?access_token={os.environ.get('access_token')}"
    return quizzes_url


@response_decorator
def get_files(course_id):

    files_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                        f"/files?access_token={os.environ.get('access_token')}&per_page=300"
    return files_url


@response_decorator
def get_file(course_id, file_id):

    files_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                f"/files/{file_id}?access_token={os.environ.get('access_token')}"
    return files_url


@response_decorator
def get_media_objects(course_id):
    media_objects_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                      f"/media_objects?access_token={os.environ.get('access_token')}&per_page=100"
    return media_objects_url



@response_decorator
def get_media_object(media_object_id):
    media_objects_url = f"{os.environ.get('API_PATH')}/media_objects/{media_object_id}" \
                        f"/media_tracks?access_token={os.environ.get('access_token')}"

    return media_objects_url



@response_decorator
def get_module_items(module_items_url):
    module_items_url = f"{module_items_url}?access_token={os.environ.get('access_token')}&per_page=100"
    return module_items_url




@response_decorator
def get_external_tools(course_id):
    external_tools_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                f"/external_tools?access_token={os.environ.get('access_token')}"
    return external_tools_url


@response_decorator
def get_external_tool(course_id, id):
    external_tools_url = f"{os.environ.get('API_PATH')}/courses/{course_id}/external_tools/sessionless_launch?url={id}" \
                         f"&access_token={os.environ.get('access_token')}"
    return external_tools_url


@response_decorator
def get_url(url):
    authenticated_url = f"{url}?access_token={os.environ.get('access_token')}"
    return authenticated_url




