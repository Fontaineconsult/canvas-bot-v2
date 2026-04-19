import os
import logging

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError, MissingSchema
import json
import warnings

from network.cred import set_canvas_api_key_to_environment_variable, load_config_data_from_appdata, get_access_token

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
    except RequestsConnectionError as exc:
        # Log and warn for connection errors
        log.error(f"Connection error: {exc} | URL: {clean_url}")
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
        warnings.warn(f"HTTP {request.status_code} - {error_message}: {clean_url}", UserWarning)
        return None


def response_decorator(calling_function):
    def wrapper(*args):
        return response_handler(calling_function(*args))
    return wrapper



@response_decorator
def get_active_accounts(page):
    active_account_url = f"{os.environ.get('API_PATH')}/accounts/1/courses?page={page}&per_page=100&access_token={get_access_token()}"
    return active_account_url



@response_decorator
def get_course(course_id):
    course_url = f"{os.environ.get('API_PATH')}/courses/{course_id}?access_token={get_access_token()}"
    return course_url


@response_decorator
def get_users_in_account(account_id):
    course_url = f"{os.environ.get('API_PATH')}/accounts/{account_id}/users?access_token={get_access_token()}"
    return course_url


@response_decorator
def get_users_scope(account_id):
    course_url = f"{os.environ.get('API_PATH')}/accounts/self/scopes?access_token={get_access_token()}"
    return course_url



@response_decorator
def get_announcements(course_id):

    announcement_url = f"{os.environ.get('API_PATH')}/announcements?context_codes=course_" \
                       f"{course_id}&access_token={get_access_token()}&per_page=100"
    return announcement_url


@response_decorator
def get_assignments(course_id):
    assignments_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                     f"/assignments?access_token={get_access_token()}&per_page=100"
    return assignments_url


@response_decorator
def get_assignment(course_id, assignment_id):
    assignment_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                     f"/assignments/{assignment_id}?access_token={get_access_token()}"
    return assignment_url


@response_decorator
def get_discussions(course_id):
    discussions_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                      f"/discussion_topics?access_token={get_access_token()}&per_page=100"

    return discussions_url


@response_decorator
def get_discussion(course_id, topic_id):
    discussions_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                      f"/discussion_topics/{topic_id}?access_token={get_access_token()}"

    return discussions_url

@response_decorator
def get_modules(course_id):
    modules_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                      f"/modules?access_token={get_access_token()}&per_page=100"

    return modules_url


@response_decorator
def get_pages(course_id):
    pages_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                      f"/pages?access_token={get_access_token()}&per_page=100"

    return pages_url

@response_decorator
def get_page(course_id, page_url):

    page_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                f"/pages/{page_url}?access_token={get_access_token()}"

    return page_url


@response_decorator
def get_quizzes(course_id):
    quizzes_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                      f"/quizzes?access_token={get_access_token()}&per_page=100"
    return quizzes_url


@response_decorator
def get_quiz(course_id, quiz_id):
    quizzes_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                  f"/quizzes/{quiz_id}?access_token={get_access_token()}"
    return quizzes_url


@response_decorator
def get_files(course_id):

    files_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                        f"/files?access_token={get_access_token()}&per_page=300"
    return files_url


@response_decorator
def get_file(course_id, file_id):

    files_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                f"/files/{file_id}?access_token={get_access_token()}"
    return files_url


@response_decorator
def get_media_objects(course_id):
    media_objects_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                      f"/media_objects?access_token={get_access_token()}&per_page=100"
    return media_objects_url



@response_decorator
def get_media_object(media_object_id):
    media_objects_url = f"{os.environ.get('API_PATH')}/media_objects/{media_object_id}" \
                        f"/media_tracks?access_token={get_access_token()}"

    return media_objects_url



@response_decorator
def get_module_items(module_items_url):
    module_items_url = f"{module_items_url}?access_token={get_access_token()}&per_page=100"
    return module_items_url


@response_decorator
def get_external_tools(course_id):
    external_tools_url = f"{os.environ.get('API_PATH')}/courses/{course_id}" \
                f"/external_tools?access_token={get_access_token()}"
    return external_tools_url


@response_decorator
def get_external_tool(course_id, id):
    external_tools_url = f"{os.environ.get('API_PATH')}/courses/{course_id}/external_tools/sessionless_launch?url={id}" \
                         f"&access_token={get_access_token()}"
    return external_tools_url


@response_decorator
def get_url(url):
    authenticated_url = f"{url}?access_token={get_access_token()}"
    return authenticated_url


def replace_file(course_id, file_id, file_path):
    """Replace a Canvas file using the 3-step upload process.

    1. GET the existing file to obtain folder_id and display_name
    2. POST to /courses/{id}/files to notify Canvas (same name + folder + on_duplicate=overwrite)
    3. POST multipart upload to the upload_url
    4. GET the redirect Location to confirm

    Returns the final file metadata dict on success, or None on failure.
    """
    # Step 0: Get existing file metadata for folder_id and display_name
    existing = get_file(course_id, file_id)
    if not existing:
        warnings.warn(f"File replace failed: could not retrieve file {file_id}", UserWarning)
        return None

    folder_id = existing.get("folder_id")
    original_name = existing.get("display_name") or existing.get("filename")
    if not folder_id or not original_name:
        warnings.warn("File replace failed: missing folder_id or filename from file metadata", UserWarning)
        return None

    filename = os.path.basename(file_path)
    filesize = os.path.getsize(file_path)

    # Enforce file type match
    original_ext = os.path.splitext(original_name)[1].lower()
    local_ext = os.path.splitext(filename)[1].lower()
    if original_ext != local_ext:
        warnings.warn(
            f"File type mismatch: Canvas file is '{original_ext}' but replacement is '{local_ext}'",
            UserWarning,
        )
        return None

    # Step 1: Notify Canvas of the upload
    notify_url = (f"{os.environ.get('API_PATH')}/courses/{course_id}"
                  f"/files?access_token={get_access_token()}")
    clean_url = _clean_url(notify_url)
    try:
        resp = requests.post(notify_url, data={
            "name": original_name,
            "size": filesize,
            "parent_folder_id": folder_id,
            "on_duplicate": "overwrite",
        }, verify=True)
    except RequestsConnectionError as exc:
        log.error(f"Connection error during file replace step 1: {exc}")
        return None

    if resp.status_code != 200:
        log.warning(f"File replace step 1 failed: {clean_url} | {resp.status_code}")
        try:
            error_message = _extract_error_message(json.loads(resp.content))
        except json.JSONDecodeError:
            error_message = resp.text
        warnings.warn(f"File replace failed (step 1): HTTP {resp.status_code} - {error_message}", UserWarning)
        return None

    upload_info = json.loads(resp.content)
    upload_url = upload_info.get("upload_url")
    upload_params = upload_info.get("upload_params", {})
    if not upload_url:
        log.error("File replace step 1 returned no upload_url")
        return None

    log.info(f"File replace step 1 OK: {clean_url}")

    # Step 2: Upload the file
    try:
        with open(file_path, "rb") as f:
            resp2 = requests.post(upload_url, data=upload_params,
                                  files={"file": (original_name, f)}, verify=True,
                                  allow_redirects=False)
    except (RequestsConnectionError, OSError) as exc:
        log.error(f"Connection error during file replace step 2: {exc}")
        return None

    # Canvas returns 3xx with Location header, or 201 with JSON
    if resp2.status_code in (301, 302, 303):
        confirm_url = resp2.headers.get("Location")
    elif resp2.status_code in (200, 201):
        try:
            result = json.loads(resp2.content)
            if result.get("id"):
                log.info(f"File replace complete (no confirmation needed): {original_name}")
                return result
            confirm_url = result.get("location")
        except json.JSONDecodeError:
            confirm_url = None
    else:
        log.warning(f"File replace step 2 failed: {resp2.status_code}")
        try:
            error_message = _extract_error_message(json.loads(resp2.content))
        except json.JSONDecodeError:
            error_message = resp2.text
        warnings.warn(f"File replace failed (step 2): HTTP {resp2.status_code} - {error_message}", UserWarning)
        return None

    if not confirm_url:
        log.error("File replace step 2 returned no confirmation URL")
        return None

    log.info("File replace step 2 OK, confirming upload")

    # Step 3: Confirm the upload (GET to the redirect Location)
    try:
        separator = "&" if "?" in confirm_url else "?"
        resp3 = requests.get(f"{confirm_url}{separator}access_token={get_access_token()}", verify=True)
    except RequestsConnectionError as exc:
        log.error(f"Connection error during file replace step 3: {exc}")
        return None

    if resp3.status_code in (200, 201):
        log.info(f"File replace complete: {original_name}")
        try:
            return json.loads(resp3.content)
        except json.JSONDecodeError:
            return {"status": "ok"}
    else:
        log.warning(f"File replace step 3 failed: {resp3.status_code}")
        try:
            error_message = _extract_error_message(json.loads(resp3.content))
        except json.JSONDecodeError:
            error_message = resp3.text
        warnings.warn(f"File replace failed (step 3): HTTP {resp3.status_code} - {error_message}", UserWarning)
        return None

