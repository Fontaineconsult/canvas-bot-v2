import re, requests, json, logging, time
from network.cred import get_youtube_api_key

from tools import logger
log = logging.getLogger(__name__)

def get_youtube_caption_info(link):


    # api_key = get_youtube_api_key()
    #
    # if not api_key:
    #     return None

    return "Not Checked"
    youtube_regex = re.compile(r'((?<=(v|V)/)|(?<=be/)|(?<=(\?|\&)v=)|(?<=embed/))([\w-]+)')
    youtube_id_search = youtube_regex.search(link)

    if youtube_id_search:

        youtube_id = youtube_id_search.group(4)
        payload = {
            'part':'snippet',
            'videoId': youtube_id,
            'key': "AIzaSyDS0BCrIzUjuJ3grm-aQiXndCAmtvaka0M",
        }

        time.sleep(0.3)
        youtube_search = requests.get("https://www.googleapis.com/youtube/v3/captions?", params=payload)

        content = json.loads(youtube_search.content.decode('utf-8'))

        if youtube_search.status_code == 403:
            print("Youtube API at Rate Limit")
            log.warning("Youtube API token is invalid")
            return None

        if youtube_search.status_code == 429:
            print("Youtube API at Rate Limit")
            log.warning("Youtube API at Rate Limit")
            return None

        if youtube_search.status_code != 200:
            log.warning("Youtube API Error Code: ", youtube_search.status_code, youtube_search.content)
            return None
        try:

            for each in content['items']:

                if each.get('snippet').get('trackKind') == "standard":
                    print("Captioned")
                    return "Captioned"
                if each.get('snippet').get('trackKind') == "asr":
                    print("Auto Caption")
                    return "Auto Caption"
        except (IndexError, KeyError):
            return "Not Captioned"

    else:
        return "Not Checked"


