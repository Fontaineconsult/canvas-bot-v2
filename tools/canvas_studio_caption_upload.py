from network.studio_api import get_captions_by_media_id, post_caption_file, get_course, get_collection_media, \
    refresh_studio_token, get_media_by_id
from network.cred import set_canvas_studio_api_key_to_environment_variable, load_config_data_from_appdata, \
    get_canvas_studio_tokens
import logging

log = logging.getLogger(__name__)


if __name__=="__main__":
    old_token, re_auth = get_canvas_studio_tokens()
    token, refresh = refresh_studio_token(re_auth)
    set_canvas_studio_api_key_to_environment_variable(token, refresh)
    load_config_data_from_appdata()


def add_caption_to_canvas_studio_video(course_id, caption_file_location, media_id):

    media = get_media_by_id(media_id)

    if media:

        current_captions = get_captions_by_media_id(media_id)
        if len(current_captions['caption_files']) > 0:
            for captions in current_captions['caption_files']:
                if captions['provider'] == "notorious":
                    break
            else:
                print("Media already has a generated caption file")
                return False

        try:
            with open(caption_file_location, 'rb') as caption_file:
                caption_file_data = caption_file.read()
                caption_file_name = caption_file_location.split("\\")[-1]
                post_caption_file(media_id, caption_file_name, caption_file_data)
        except FileNotFoundError as exc:
            log.exception(exc)
            print(exc)
            return False

    else:
        print("Media ID not found in collection. Check if it is imported into the canvas course")
        return False





def check_media_id(course_id, media_id):

    course = get_course(course_id)
    collection_id = course['course']['id']
    collection = get_collection_media(collection_id)

    for item in collection['media']:
        print(item)
        if str(item['id']) == str(media_id):
            break
    else:
        print("Media ID not found in collection. Check if it is imported into the canvas course")
        return False

    return True

