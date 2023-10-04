from network.studio_api import get_captions_by_media_id, post_caption_file, get_course, get_collection_media, \
    refresh_studio_token
from network.cred import set_canvas_studio_api_key_to_environment_variable, load_config_data_from_appdata, \
    get_canvas_studio_tokens
import logging
log = logging.getLogger(__name__)


if __name__=="__main__":
    old_token, re_auth = get_canvas_studio_tokens()
    token, refresh = refresh_studio_token(re_auth)
    set_canvas_studio_api_key_to_environment_variable(token, refresh)
    load_config_data_from_appdata()


def add_caption_to_canvas_studio_video(course_id, media_id, caption_file_location):

    course = get_course(course_id)
    collection_id = course['course']['id']
    collection = get_collection_media(collection_id)

    for item in collection['media']:
        if item['id'] == media_id:
            break
    else:
        return False, "Media ID not found in collection."

    current_captions = get_captions_by_media_id(media_id)

    if len(current_captions['caption_files']) > 0:
        for captions in current_captions['caption_files']:
            if captions['status'] == "generated":
                break
        else:
            return False, "Media already has a generated caption file"

    try:
        with open(caption_file_location, 'rb') as caption_file:
            caption_file_data = caption_file.read()
            caption_file_name = caption_file_location.split("\\")[-1]
            post_caption_file(media_id, caption_file_name, caption_file_data)
    except FileNotFoundError as exc:
        log.exception(exc)
        return False, exc


