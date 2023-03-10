from datetime import datetime
from typing import List


def get_order(node) -> int:

    path_list = build_path(node)
    for node_ in path_list:
        if node_.__dict__.get("position") is not None:
            return node_.__dict__.get("position")
    return 0


def is_hidden(node) -> bool:

    path_list = build_path(node)

    for node_ in path_list:
        if node_.__dict__.get("hidden_for_user") is True\
                or node_.__dict__.get('published') is False\
                or node_.__dict__.get("hide_from_students") is True:
            return True
        return False


def build_path(node) -> List:
    path_list = list()

    def get_parent(node_):

        if hasattr(node_, "root_node"):
            path_list.append(node_)
        if not hasattr(node_, "root_node"):
            path_list.append(node_)
            get_parent(node_.parent)
    get_parent(node)
    return path_list



def main_dict(**items) -> dict:

    main_dict = {
        "content_type": items.get("content_type"),
        "course_title": items.get("course_title"),
        "course_id": items.get("course_id"),
        "course_url": items.get("course_url"),
        "content": list(),
        "count": items.get("count")
    }
    return main_dict



def document_dict(document_node):

    document_dict = {

        "title": getattr(document_node, "title", None),
        "url": getattr(document_node, "url", None),
        "source_page_type": document_node.parent.__class__.__name__,
        "source_page_url": getattr(document_node.parent, "html_url", None),
        # "source_page_title": document_node.parent.html_url,
        "scan_date": datetime.now(),
        "is_hidden": is_hidden(document_node),
        "file_type": getattr(document_node, "mime_class", None),
        "order": get_order(document_node),
        # "path": build_path(document_node),


    }
    return document_dict


def document_site_dict(**items):

    document_site_dict = {

        "title": items.get("title"),
        "url": items.get("url"),
        "download_url": items.get("download_url"),
        "source_page_type": items.get("source_page_type"),
        "source_page_url": items.get("source_page_url"),
        "source_page_title": items.get("source_page_title"),
        "scan_date": datetime.now(),
        "is_hidden": items.get("is_hidden"),
        "content_type": items.get("content_type"),
        "mime_type": items.get("mime_type"),
        "order": items.get("order"),
        "downloadable": items.get("downloadable"),
        "path": items.get('path'),
        "title_path": items.get("title_path"),
        "uri_path": items.get("uri_path")

    }
    return document_site_dict



def video_site_dict(video_site_node):

    video_site_dict = {

        "title": getattr(video_site_node, "title", None),
        "url": getattr(video_site_node, "url", None),
        "source_page_type": video_site_node.parent.__class__.__name__,
        "source_page_url": getattr(video_site_node.parent, "html_url", None),
        # "source_page_title": document_node.parent.html_url,
        "scan_date": datetime.now(),
        "is_hidden": is_hidden(video_site_node),
        "order": get_order(video_site_node),
        # "path": build_path(video_site_node),

    }
    return video_site_dict


def video_file_dict(video_file_node):

    video_file_dict = {

        "title": getattr(video_file_node, "title", None),
        "url": getattr(video_file_node, "url", None),
        "source_page_type": video_file_node.parent.__class__.__name__,
        "source_page_url": getattr(video_file_node.parent, "html_url", None),
        # "source_page_title": document_node.parent.html_url,
        "scan_date": datetime.now(),
        "is_hidden": is_hidden(video_file_node),
        "file_type": getattr(video_file_node, "mime_class", None),
        "order": get_order(video_file_node),
        # "path": build_path(document_node),

    }
    return video_file_dict


def audio_file_dict(**items):

    audio_file_dict = {

        "title": items.get("title"),
        "url": items.get("url"),
        "download_url": items.get("download_url"),
        "source_page_type": items.get("source_page_type"),
        "source_page_url": items.get("source_page_url"),
        "source_page_title": items.get("source_page_title"),
        "scan_date": datetime.now(),
        "is_hidden": items.get("is_hidden"),
        "content_type": items.get("content_type"),
        "mime_type": items.get("mime_type"),
        "order": items.get("order"),
        "downloadable": items.get("downloadable"),
        "path": items.get('path'),
        "title_path": items.get("title_path"),
        "uri_path": items.get("uri_path")

    }
    return audio_file_dict


def audio_site_dict(**items):

    audio_site_dict = {

        "title": items.get("title"),
        "url": items.get("url"),
        "download_url": items.get("download_url"),
        "source_page_type": items.get("source_page_type"),
        "source_page_url": items.get("source_page_url"),
        "source_page_title": items.get("source_page_title"),
        "scan_date": datetime.now(),
        "is_hidden": items.get("is_hidden"),
        "content_type": items.get("content_type"),
        "mime_type": items.get("mime_type"),
        "order": items.get("order"),
        "downloadable": items.get("downloadable"),
        "path": items.get('path'),
        "title_path": items.get("title_path"),
        "uri_path": items.get("uri_path")

    }
    return audio_site_dict



def image_file_dict(**items):

    image_file_dict = {

        "title": items.get("title"),
        "url": items.get("url"),
        "download_url": items.get("download_url"),
        "source_page_type": items.get("source_page_type"),
        "source_page_url": items.get("source_page_url"),
        "source_page_title": items.get("source_page_title"),
        "scan_date": datetime.now(),
        "is_hidden": items.get("is_hidden"),
        "content_type": items.get("content_type"),
        "mime_type": items.get("mime_type"),
        "order": items.get("order"),
        "downloadable": items.get("downloadable"),
        "path": items.get('path'),
        "title_path": items.get("title_path"),
        "uri_path": items.get("uri_path")

    }
    return image_file_dict



def unsorted_dict(**items):

    unsorted_dict = {

        "title": items.get("title"),
        "url": items.get("url"),
        "download_url": items.get("download_url"),
        "source_page_type": items.get("source_page_type"),
        "source_page_url": items.get("source_page_url"),
        "source_page_title": items.get("source_page_title"),
        "scan_date": datetime.now(),
        "is_hidden": items.get("is_hidden"),
        "content_type": items.get("content_type"),
        "mime_type": items.get("mime_type"),
        "order": items.get("order"),
        "downloadable": items.get("downloadable"),
        "path": items.get('path'),
        "title_path": items.get("title_path"),
        "uri_path": items.get("uri_path")

    }
    return unsorted_dict