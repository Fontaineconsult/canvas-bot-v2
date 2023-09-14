import json
import os

import requests

from network.cred import get_canvas_studio_client_credentials, load_config_data_from_appdata

# access_token = "-jj7mrzSn8agkTl0YhhSGi8fzezDL2ORSfHPIenBMf4"
# TokenType = "Bearer"
# expires_in = "7200"
# refresh_token = "g8nf3fu778NwDFxAB3_T3qErqMoMGukpZprgMOTxPbg"
# created_at = "1693587319"
# auth_url = "https://sfsu.instructuremedia.com/api/public/oauth/authorize"
# access_token_url = "https://sfsu.instructuremedia.com/api/public/oauth/token"
# client_id = "AwcmL_ig_gCsDeWVQUPw3Cw_BhP7R4k-z6Gtru4bzu8"
# client_secret = "4PY0DtFQHwzkQBytckdTvvigjPOFGx3WZJZMyljbMa8"
# timestamp = 1693587320015



def authorize_studio_token():

    import requests
    import webbrowser


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
            'redirect_uri': os.environ['STUDIO_CALLBACK_URL'],
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






def refresh_studio_token(old_refresh_token: str,
                         client_id: str,
                         client_secret: str):

    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': old_refresh_token,
        'client_id': client_id,
        'client_secret': client_secret
    }

    response = requests.post(access_token_url, data=payload)
    response_data = response.json()

    if response.status_code == 200:
        new_access_token = response_data['access_token']
        new_refresh_token = response_data['refresh_token']
        return new_access_token, new_refresh_token
    else:
        print("Error refreshing token:", response_data)
    return None


def response_handler(request_url):


    headers = {"accept": "application/json",
               "Authorization": f"Bearer {access_token}"}

    request = requests.get(request_url, headers=headers)
    return json.loads(request.content)


def download_handler(request_url):

    headers = {"accept": "application/json",
               "Authorization": f"Bearer {access_token}"}

    request = requests.get(request_url, headers=headers)
    print(request)
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

print(get_course('4345'))
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
