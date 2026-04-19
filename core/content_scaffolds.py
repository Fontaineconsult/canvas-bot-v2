from datetime import datetime
from urllib.parse import unquote_plus

from core.downloader import path_constructor, derive_file_name
from core.utilities import build_path, is_hidden, get_hidden_reasons
from tools.captioning_check import get_youtube_caption_info
from tools.string_checking.other_tools import get_extension_from_filename, get_extension_from_mime_type




def _ext(name: str | None) -> str | None:
    """Extract lowercase extension (without dot) from a filename, or None."""
    if not name:
        return None
    ext = get_extension_from_filename(name)
    return ext.lower() if ext else None


def get_file_type(node) -> str | None:
    """Derive file type (extension) from a content node using a priority fallback chain."""
    # 1. Extension from display_name (most reliable human-readable name)
    ext = _ext(getattr(node, "display_name", None))
    if ext:
        return ext

    # 2. Extension from file_name
    ext = _ext(getattr(node, "file_name", None))
    if ext:
        return ext

    # 3. Extension from filename (URL-decoded)
    if getattr(node, "filename", None):
        ext = _ext(unquote_plus(node.filename))
        if ext:
            return ext

    # 4. mime_class (Canvas short label: "pdf", "doc", "ppt", etc.)
    if getattr(node, "mime_class", None):
        return node.mime_class

    # 5. Extension from mime_type via mimetypes module
    if getattr(node, "mime_type", None):
        guessed = get_extension_from_mime_type(node.mime_type)
        if guessed:
            return guessed.lstrip(".")

    # 6. Extension from title
    ext = _ext(getattr(node, "title", None))
    if ext:
        return ext

    # 7. Extension from url
    if getattr(node, "url", None):
        ext = _ext(node.url.split("?")[0].split("/")[-1])
        if ext:
            return ext

    return None


def get_source_page_url(node) -> str:

    """
    Get the url of the page that the node is on.
    :param node:
    :return:
    """
    if getattr(node.parent, "html_url", None):
        return getattr(node.parent, "html_url")

    else:
        if node.parent.__class__.__name__ == "Module":
            url = getattr(node.parent, "url", None)
            return f"{url}/modules#{node.parent.id}"
        else:
            return getattr(node.parent, "url", None)

def return_node_of_type(node, node_type):

    """
    recursively check if the node is of the node_type
    :param node:
    :param node_type:
    :return:
    """

    if hasattr(node, "root_node"):
        return False

    if node.__class__.__name__ == node_type:
        return node
    else:
        if node.parent:
            return return_node_of_type(node.parent, node_type)
        else:
            return False

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





def main_dict(**items) -> dict:

    main_dict = {

        "course_id": items.get("course_id"),
        "course_url": items.get("course_url"),
        "content": list(),
        "count": items.get("count"),
        "amount:": items.get("amount"),

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
        "hidden_reason": get_hidden_reasons(document_node),
        "file_source": "Canvas" if getattr(document_node, "is_canvas_file", False) else "External File",
        "canvas_file_id": getattr(document_node, "id", None),
        "file_type": get_file_type(document_node),
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
        "hidden_reason": get_hidden_reasons(document_site_node),
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
        "hidden_reason": get_hidden_reasons(video_site_node),
        "order": get_order(video_site_node),
        "is_captioned": getattr(video_site_node, "captioned", False),
        "path": [node.title for node in build_path(video_site_node, ignore_root=True) if node.title is not None],
        "class": video_site_node.__class__.__name__,


    }

    if check_caption_status:
        video_site_dict["caption_status"] = get_youtube_caption_info(getattr(video_site_node, "url", None))

    return video_site_dict


def video_file_dict(video_file_node, file_download_directory, flatten):

    # check_if_canvas_media_in_shell(video_file_node)

    video_file_dict = {

        "title": getattr(video_file_node, "title", None),
        "file_name": derive_file_name(video_file_node),
        "url": getattr(video_file_node, "url", None),
        "source_page_type": video_file_node.parent.__class__.__name__,
        "source_page_url": get_source_page_url(video_file_node),
        # "source_page_title": document_node.parent.html_url,
        "scan_date": datetime.now(),
        "is_hidden": is_hidden(video_file_node),
        "hidden_reason": get_hidden_reasons(video_file_node),
        "file_type": get_file_type(video_file_node),
        "order": get_order(video_file_node),
        "is_captioned": getattr(video_file_node, "captioned", False),
        "download_url": getattr(video_file_node, "download_url", getattr(video_file_node, "url", None)),
        "path": [node.title for node in build_path(video_file_node, ignore_root=True) if node.title is not None],
        "class": video_file_node.__class__.__name__,

    }

    if getattr(video_file_node, "media_entry_id", None):
        video_file_dict['canvas_media_id'] = video_file_node.media_entry_id

    if getattr(video_file_node, "uuid", None):
        video_file_dict['canvas_media_id'] = video_file_node.uuid


    if getattr(video_file_node, "media_id", None):
        video_file_dict['canvas_media_id'] = video_file_node.media_id

    if file_download_directory:
        video_file_dict["save_path"] = path_constructor(file_download_directory, video_file_node, flatten)

    if video_file_node.is_canvas_studio_file:
        video_file_dict["canvas_studio_id"] = getattr(video_file_node, 'id', None)

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
        "hidden_reason": get_hidden_reasons(audio_file_node),
        "file_type": get_file_type(audio_file_node),
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
        "hidden_reason": get_hidden_reasons(audio_site_node),
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
        "hidden_reason": get_hidden_reasons(image_file_node),
        "file_type": get_file_type(image_file_node),
        "order": get_order(image_file_node),
        "path": [node.title for node in build_path(image_file_node, ignore_root=True) if node.title is not None],
    }

    if file_download_directory:
        image_file_dict["save_path"] = path_constructor(file_download_directory, image_file_node, flatten)

    return image_file_dict



def digital_textbook_dict(node):

    digital_textbook_dict = {

        "title": getattr(node, "title", None),
        "url": getattr(node, "url", None),
        "source_page_type": node.parent.__class__.__name__,
        "source_page_url": get_source_page_url(node),
        "scan_date": datetime.now(),
        "is_hidden": is_hidden(node),
        "hidden_reason": get_hidden_reasons(node),
        "order": get_order(node),
        "path": [n.title for n in build_path(node, ignore_root=True) if n.title is not None],

    }
    return digital_textbook_dict


def institution_video_dict(node):

    institution_video_dict = {

        "title": getattr(node, "title", None),
        "url": getattr(node, "url", None),
        "source_page_type": node.parent.__class__.__name__,
        "source_page_url": get_source_page_url(node),
        "scan_date": datetime.now(),
        "is_hidden": is_hidden(node),
        "hidden_reason": get_hidden_reasons(node),
        "order": get_order(node),
        "path": [n.title for n in build_path(node, ignore_root=True) if n.title is not None],

    }
    return institution_video_dict


def file_storage_dict(node):

    file_storage_dict = {

        "title": getattr(node, "title", None),
        "url": getattr(node, "url", None),
        "source_page_type": node.parent.__class__.__name__,
        "source_page_url": get_source_page_url(node),
        "scan_date": datetime.now(),
        "is_hidden": is_hidden(node),
        "hidden_reason": get_hidden_reasons(node),
        "order": get_order(node),
        "path": [n.title for n in build_path(node, ignore_root=True) if n.title is not None],

    }
    return file_storage_dict


def unsorted_dict(unsorted_node):

    unsorted_dict = {

        "title": getattr(unsorted_node, "title", None),
        "url": getattr(unsorted_node, "url", None),
        "source_page_type": unsorted_node.parent.__class__.__name__,
        "source_page_url": get_source_page_url(unsorted_node),
        # "source_page_title": document_node.parent.html_url,
        "scan_date": datetime.now(),
        "is_hidden": is_hidden(unsorted_node),
        "hidden_reason": get_hidden_reasons(unsorted_node),
        "order": get_order(unsorted_node),
        "path": [node.title for node in build_path(unsorted_node, ignore_root=True) if node.title is not None],

    }
    return unsorted_dict