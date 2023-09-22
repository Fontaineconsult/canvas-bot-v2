import base64
import json
import logging
import os
import warnings

import requests
from requests.exceptions import MissingSchema, JSONDecodeError

log = logging.getLogger(__name__)
def authorize_studio_token():

    import requests
    import webbrowser
    from network.cred import get_canvas_studio_client_credentials, load_config_data_from_appdata

    # Step 1: Redirect user to authorization URL
    load_config_data_from_appdata()
    studio_client_credentials = get_canvas_studio_client_credentials()

    if studio_client_credentials:
        client_id, client_secret = studio_client_credentials


        CANVAS_STUDIO_AUTHENTICATION_URL = os.environ['CANVAS_STUDIO_AUTHENTICATION_URL']
        CANVAS_STUDIO_TOKEN_URL = os.environ['CANVAS_STUDIO_TOKEN_URL']
        CANVAS_STUDIO_CALLBACK_URL = os.environ['CANVAS_STUDIO_CALLBACK_URL']


        auth_params = {
            'client_id': client_id,
            'response_type': 'code',
            'redirect_uri': CANVAS_STUDIO_CALLBACK_URL
        }


        authorization_redirect_url = CANVAS_STUDIO_AUTHENTICATION_URL + '?' + '&'.join([f"{k}={v}" for k, v in auth_params.items()])

        webbrowser.open(authorization_redirect_url)

        # Get the authorization code from the callback URL
        auth_code = input("Enter the authorization code: ")

        # Step 2: Exchange the authorization code for an access token and refresh token


        token_payload = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': os.environ['CANVAS_STUDIO_CALLBACK_URL'],
            'client_id': client_id,
            'client_secret': client_secret
        }

        response = requests.post(CANVAS_STUDIO_TOKEN_URL, data=token_payload)
        token_data = response.json()


        if response.status_code == 200:
            access_token = token_data['access_token']
            refresh_token = token_data['refresh_token']
            return access_token, refresh_token


        else:
            print("Error obtaining tokens:", token_data)

def refresh_studio_token(reauth_token: str):

    from network.cred import load_config_data_from_appdata, get_canvas_studio_client_credentials

    studio_client_id, studio_client_secret = get_canvas_studio_client_credentials()

    if not studio_client_id or not studio_client_secret:
        print("Error: Canvas Studio Client ID or Client Secret not found. Can't refresh token")
        return None

    # Generate the Authorization header value
    credentials = f"{studio_client_id}:{studio_client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': reauth_token
    }

    load_config_data_from_appdata()

    try:
        CANVAS_STUDIO_TOKEN_URL = os.environ['CANVAS_STUDIO_TOKEN_URL']
    except KeyError:
        print("Error: Canvas Studio Token URL not found")
        return None

    response = requests.post(CANVAS_STUDIO_TOKEN_URL, data=payload, headers=headers)
    response_data = response.json()

    if response.status_code == 200:
        print("Studio Token Refresh Successful")
        new_access_token = response_data['access_token']
        new_refresh_token = response_data['refresh_token']
        print(new_refresh_token, new_access_token)
        return new_access_token, new_refresh_token
    else:
        print("Error refreshing token:", response_data)
        print("Reauthorizing token")
        authorize_studio_token()
    return None


def response_handler(request_url):


    headers = {"accept": "application/json",
               "Authorization": f"Bearer {os.environ['CANVAS_STUDIO_TOKEN']}"}

    try:
        request = requests.get(request_url, headers=headers)
    except requests.exceptions.ConnectionError as exc:
        log.exception(f"{exc} {request_url}")
        warnings.warn(f"{exc} {request_url}", UserWarning)
        return False
    except MissingSchema as exc:
        log.exception(f"{exc} {request_url}")
        warnings.warn(f"{exc} {request_url}", UserWarning)
        return None
    if request.status_code == 200:
        log.info(f"Request: {request_url} | Status Code: {request.status_code}")
        return json.loads(request.content)
    if request.status_code != 200:
        log.warning(f"Request: {request_url} | Status Code: {request.status_code}")
        try:
            error_message = json.loads(request.content)
        except JSONDecodeError as exc:
            log.exception(f"{exc} {request_url}")
            error_message = "Failed to load message"
        warning_message = f"{request.status_code} {error_message} {request_url}"
        warnings.warn(warning_message, UserWarning)
        return None


def download_handler(request_url):

    headers = {"accept": "application/json",
               "Authorization": f"Bearer {os.environ['CANVAS_STUDIO_TOKEN']}"}
    request = requests.get(request_url, headers=headers)
    return request.content


def response_decorator(calling_function):
    def wrapper(*args):
        return response_handler(calling_function(*args))
    return wrapper


def download_decorator(calling_function):
    def wrapper(*args):
        return download_handler(calling_function(*args))
    return wrapper


@response_decorator
def get_course(course_id):
    course_url = f"https://sfsu.instructuremedia.com/api/public/v1/courses/{course_id}"
    return course_url


@response_decorator
def get_collection_media(collection_id):
    course_url = f"https://sfsu.instructuremedia.com/api/public/v1/collections/{collection_id}/media"
    return course_url

@response_decorator
def get_collections_permission():
    course_url = f"https://sfsu.instructuremedia.com/api/public/v1/collections/"
    return course_url


@response_decorator
def get_collections_data(collection_id):
    course_url = f"https://sfsu.instructuremedia.com/api/public/v1/collections/{collection_id}"
    return course_url


@response_decorator
def search_user(email):
    course_url = f"https://sfsu.instructuremedia.com/api/public/v1/users/search?email={email}"
    return course_url

@response_decorator
def get_user_media(user_id):
    course_url = f"https://sfsu.instructuremedia.com/api/public/v1/users/{user_id}/media"
    return course_url


@response_decorator
def get_courses_containing_media(media_id):
    course_url = f"https://sfsu.instructuremedia.com/api/public/v1/media/{media_id}/courses"
    return course_url


@response_decorator
def get_media_by_id(media_id):
    course_url = f"https://sfsu.instructuremedia.com/api/public/v1/media/{media_id}"
    return course_url

@response_decorator
def get_media_sources_by_id(media_id):
    course_url = f"https://sfsu.instructuremedia.com/api/public/v1/media/{media_id}/sources"
    return course_url


@response_decorator
def get_media_shares(media_id):
    course_url = f"https://sfsu.instructuremedia.com/api/public/v1/media/{media_id}/permissions"
    return course_url


@response_decorator
def get_captions_by_media_id(media_id):
    course_url = f"https://sfsu.instructuremedia.com/api/public/v1/media/{media_id}/caption_files"
    return course_url


@download_decorator
def download_caption_by_caption_file_id(caption_file_id):
    course_url = f"https://sfsu.instructuremedia.com/api/public/v1/caption_files/{caption_file_id}/download"
    return course_url
