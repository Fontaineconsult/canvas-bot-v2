from datetime import datetime
from typing import List

from core.downloader import path_constructor, derive_file_name
from tools.captioning_check import get_youtube_caption_info


def get_source_page_url(node) -> int:

    """
    Get the url of the page that the node is on.
    :param node:
    :return:
    """
    if getattr(node.parent, "html_url", None):
        return getattr(node.parent, "html_url")

    else:
        return getattr(node.parent, "url", None)


def get_order(node) -> int:

    """
    Get the order of the node in the course.
    :param node:
    :return:
    """

    path_list = build_path(node)
    for node_ in path_list:
        if node_.__dict__.get("position") is not None:
            return node_.__dict__.get("position")
    return 0


def is_hidden(node) -> bool:

    """
    Check if the node is hidden.
    :param node:
    :return:
    """

    # don't print node, will cause max recursion error
    path_list = build_path(node)

    for node_ in path_list:
        if node_.__dict__.get("hidden_for_user") is True\
                or node_.__dict__.get('published') is False\
                or node_.__dict__.get("hide_from_students") is True \
                or node_.__dict__.get("locked") is True:
            return True
        return False



def build_path(node, ignore_root=False) -> List:

    """
    Build a list of the path from the node to the root node.
    :param node:
    :param ignore_root:
    :return:
    """

    path_list = list()

    def get_parent(node_):

        if hasattr(node_, "root_node"):

            if not ignore_root:
                pass
            else:
                path_list.append(node_)
        if not hasattr(node_, "root_node"):

            path_list.append(node_)
            get_parent(node_.parent)
    get_parent(node)
    return path_list



def main_dict(**items) -> dict:

    main_dict = {

        "course_id": items.get("course_id"),
        "course_url": items.get("course_url"),
        "content": list(),
        "count": items.get("count")
    }
    return main_dict



def document_dict(document_node, file_download_directory, flatten):

    document_dict = {

        "title": getattr(document_node, "title", None),
        "url": getattr(document_node, "url", None),
        "source_page_type": document_node.parent.__class__.__name__,
        "source_page_url": get_source_page_url(document_node),
        # "source_page_title": document_node.parent.html_url,
        "scan_date": datetime.now(),
        "is_hidden": is_hidden(document_node),
        "file_type": getattr(document_node, "mime_class", None),
        "order": get_order(document_node),
        "path": [node.title for node in build_path(document_node, ignore_root=True) if node.title is not None],
    }

    if file_download_directory:
        document_dict["save_path"] = path_constructor(file_download_directory, document_node, flatten)

    return document_dict


def document_site_dict(document_site_node):

    document_site_dict = {

        "title": getattr(document_site_node, "title", None),
        "file_name": derive_file_name(document_site_node),
        "url": getattr(document_site_node, "url", None),
        "source_page_type": document_site_node.parent.__class__.__name__,
        "source_page_url": get_source_page_url(document_site_node),
        # "source_page_title": document_node.parent.html_url,
        "scan_date": datetime.now(),
        "is_hidden": is_hidden(document_site_node),
        "order": get_order(document_site_node),
        "path": [node.title for node in build_path(document_site_node, ignore_root=True) if node.title is not None],

    }
    return document_site_dict



def video_site_dict(video_site_node, check_caption_status):

    video_site_dict = {

        "title": getattr(video_site_node, "title", None),
        "url": getattr(video_site_node, "url", None),
        "source_page_type": video_site_node.parent.__class__.__name__,
        "source_page_url": get_source_page_url(video_site_node),
        # "source_page_title": document_node.parent.html_url,
        "scan_date": datetime.now(),
        "is_hidden": is_hidden(video_site_node),
        "order": get_order(video_site_node),
        "is_captioned": getattr(video_site_node, "captioned", False),
        "path": [node.title for node in build_path(video_site_node, ignore_root=True) if node.title is not None],

    }

    if check_caption_status:
        video_site_dict["caption_status"] = get_youtube_caption_info(getattr(video_site_node, "url", None))


    return video_site_dict


def video_file_dict(video_file_node, file_download_directory, flatten):

    video_file_dict = {

        "title": getattr(video_file_node, "title", None),
        "file_name": derive_file_name(video_file_node),
        "url": getattr(video_file_node, "url", None),
        "source_page_type": video_file_node.parent.__class__.__name__,
        "source_page_url": get_source_page_url(video_file_node),
        # "source_page_title": document_node.parent.html_url,
        "scan_date": datetime.now(),
        "is_hidden": is_hidden(video_file_node),
        "file_type": getattr(video_file_node, "mime_class", None),
        "order": get_order(video_file_node),
        "is_captioned": getattr(video_file_node, "captioned", False),
        "download_url": getattr(video_file_node, "download_url", getattr(video_file_node, "url", None)),
        "path": [node.title for node in build_path(video_file_node, ignore_root=True) if node.title is not None],


    }

    if file_download_directory:
        video_file_dict["save_path"] = path_constructor(file_download_directory, video_file_node, flatten)

    video_file_dict["canvas_studio_id"] = getattr(video_file_node, "id", None)

    if getattr(video_file_node, "captions_list", None):

        if len(video_file_node.captions_list) == 1:

            if video_file_node.captions_list[0]["provider"] == 'notorious':
                video_file_dict["machine_captioned"] = True
            else:
                video_file_dict["machine_captioned"] = False
        else:
            video_file_dict["machine_captioned"] = False

    return video_file_dict


def audio_file_dict(audio_file_node, file_download_directory, flatten):

    audio_file_dict = {

        "title": getattr(audio_file_node, "title", None),
        "file_name": derive_file_name(audio_file_node),
        "url": getattr(audio_file_node, "url", None),
        "source_page_type": audio_file_node.parent.__class__.__name__,
        "source_page_url": get_source_page_url(audio_file_node),
        # "source_page_title": document_node.parent.html_url,
        "scan_date": datetime.now(),
        "is_hidden": is_hidden(audio_file_node),
        "file_type": getattr(audio_file_node, "mime_class", None),
        "order": get_order(audio_file_node),
        "path": [node.title for node in build_path(audio_file_node, ignore_root=True) if node.title is not None],
    }

    if file_download_directory:
        audio_file_dict["save_path"] = path_constructor(file_download_directory, audio_file_node, flatten)

    return audio_file_dict


def audio_site_dict(audio_site_node):

    audio_site_dict = {

        "title": getattr(audio_site_node, "title", None),
        "url": getattr(audio_site_node, "url", None),
        "source_page_type": audio_site_node.parent.__class__.__name__,
        "source_page_url": get_source_page_url(audio_site_node),
        # "source_page_title": document_node.parent.html_url,
        "scan_date": datetime.now(),
        "is_hidden": is_hidden(audio_site_node),
        "order": get_order(audio_site_node),
        "path": [node.title for node in build_path(audio_site_node, ignore_root=True) if node.title is not None],

    }
    return audio_site_dict



def image_file_dict(image_file_node, file_download_directory, flatten):

    image_file_dict = {

        "title": getattr(image_file_node, "title", None),
        "file_name": derive_file_name(image_file_node),
        "url": getattr(image_file_node, "url", None),
        "source_page_type": image_file_node.parent.__class__.__name__,
        "source_page_url": get_source_page_url(image_file_node),
        # "source_page_title": document_node.parent.html_url,
        "scan_date": datetime.now(),
        "is_hidden": is_hidden(image_file_node),
        "file_type": getattr(image_file_node, "mime_class", None),
        "order": get_order(image_file_node),
        "path": [node.title for node in build_path(image_file_node, ignore_root=True) if node.title is not None],
    }

    if file_download_directory:
        image_file_dict["save_path"] = path_constructor(file_download_directory, image_file_node, flatten)

    return image_file_dict



def unsorted_dict(unsorted_node):

    unsorted_dict = {

        "title": getattr(unsorted_node, "title", None),
        "url": getattr(unsorted_node, "url", None),
        "source_page_type": unsorted_node.parent.__class__.__name__,
        "source_page_url": get_source_page_url(unsorted_node),
        # "source_page_title": document_node.parent.html_url,
        "scan_date": datetime.now(),
        "is_hidden": is_hidden(unsorted_node),
        "order": get_order(unsorted_node),
        "path": [node.title for node in build_path(unsorted_node, ignore_root=True) if node.title is not None],

    }
    return unsorted_dict