from datetime import datetime


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



def document(node):

    document_dict = {

        "title": getattr(node, "title", None),
        "url": getattr(node, "url", None),
        # "download_url": items.get("download_url"),
        # "source_page_type": items.get("source_page_type"),
        # "source_page_url": items.get("source_page_url"),
        # "source_page_title": items.get("source_page_title"),
        # "scan_date": datetime.now(),
        # "is_hidden": items.get("is_hidden"),
        # "content_type": items.get("content_type"),
        # "mime_type": items.get("mime_type"),
        # "order": items.get("order"),
        # "downloadable": items.get("downloadable"),
        # "path": items.get('path'),
        # "title_path": items.get("title_path"),
        # "uri_path": items.get("uri_path")

    }
    return document_dict


def document_site(**items):

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



def video_site(**items):

    video_site_dict = {

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
    return video_site_dict


def video_file(**items):

    video_file_dict = {

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
    return video_file_dict


def audio_file(**items):

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


def audio_site(**items):

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



def image_file(**items):

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



def unsorted(**items):

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