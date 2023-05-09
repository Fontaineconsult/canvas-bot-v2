from __future__ import annotations

from os import path

from resource_nodes.base_content_node import BaseContentNode
from sorters.sorters import force_to_shortcut, file_name_extractor
from datetime import datetime

import win32com.client
import os.path
from typing import TYPE_CHECKING
import requests
from requests.exceptions import MissingSchema, InvalidURL, SSLError
from config.yaml_io import read_config, read_download_manifest, write_to_download_manifest
from tools.string_checking.url_cleaning import sanitize_windows_filename, remove_trailing_path_segments

config = read_config()

user_agent = config['requests']['user-agent']
default_download_path = config['default_download_path']


import logging
import tools.logger
log = logging.getLogger(__name__)


from tools.string_checking.other_tools import has_file_extension, remove_query_params_from_url

if TYPE_CHECKING:
    from core.content_extractor import ContentExtractor


def derive_filename_from_url(contentnode: BaseContentNode):
    """
    Derives a filename from a URL.
    :param contentnode: The content node to derive the filename from.
    :return:

    """
    remove_trailing = remove_trailing_path_segments(contentnode.url)
    if remove_trailing:
        return remove_trailing.split('/')[-1]
    else:
        return f"$$-{contentnode.title[:20]}" # force a filename to a shortcut using $$- as a prefix

def sort_by_date():
    return datetime.now().strftime('%d-%m-%Y')


def derive_file_name(node):

    if not has_file_extension(node.title):

        filename = derive_filename_from_url(node)
    else:
        try:
            filename = sanitize_windows_filename(file_name_extractor.match(node.title.split('/')[-1]).group(0))
        except AttributeError:
            filename = sanitize_windows_filename(node.title)
    return filename


def path_constructor(root_directory: str, node: BaseContentNode, flatten: bool):
    from core.content_scaffolds import is_hidden, build_path

    """
        Returns the path to the folder that the file should be saved in.
    """

    filename = sanitize_windows_filename(derive_file_name(node))

    node_path = build_path(node, ignore_root=True)
    paths = list()

    if flatten:
        paths.append(sanitize_windows_filename(node.title[:50], folder=True).rstrip()
                     if node.title else str(node.__class__.__name__))

        return os.path.join(root_directory, sort_by_date(),  f"{node.__class__.__name__}s", filename)

    for node_ in node_path:
        if hasattr(node_, 'is_resource'):
            paths.append(sanitize_windows_filename(node_.title[:50], folder=True).rstrip() if node_.title else str(node_.__class__.__name__))

    constructed_path = os.path.join(root_directory, sort_by_date(), *paths[::-1], f"{node.__class__.__name__}s", filename)

    if len(constructed_path) > 260:

        filename_, extension = os.path.splitext(filename)

        if len(extension) > 5:
            extension = extension[:5]
        shortened_filename = f"{filename_[:20]}{extension}"
        constructed_path = constructed_path.replace(filename, shortened_filename)
    return constructed_path


def create_windows_shortcut_from_url(url: str, shortcut_path: str):
    """
    Creates a Windows shortcut (.lnk) file from a URL.
    :param url: The URL to create the shortcut from.
    :param shortcut_path: The path to save the shortcut to.
    """

    encode_path_to_ascii = shortcut_path.encode('ascii', errors='ignore').decode('ascii')
    shortcut_path = encode_path_to_ascii.split(".")[0] + ".lnk"

    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = url
        shortcut.save()
        return shortcut_path
    except Exception as exc:
        log.exception(f"Failed to create shortcut for {url} at {shortcut_path} because of {exc}")
        raise exc



class DownloaderMixin:
    """
    A mixin class for the ContentExtractor class that provides methods for downloading files.
    """

    def download(self, content_extractor: ContentExtractor, root_directory: str, **params):
        from core.content_scaffolds import is_hidden
        download_manifest = read_download_manifest(root_directory)['downloaded_files']

        log.info(f"Downloading files to {root_directory} with params: {params}")

        include_video_files = params.get('include_video_files', False)
        include_audio_files = params.get('include_audio_files', False)
        include_image_files = params.get('include_image_files', False)
        flatten = params.get('flatten', False)
        download_hidden_files = params.get('download_hidden_files', False)

        if not root_directory:
            print(f"Using default download path: {os.path.dirname(os.path.abspath(__file__))}")
            directory = os.path.dirname(os.path.abspath(__file__))

        download_nodes = [ContentNode for ContentNode in content_extractor.get_document_objects()]

        if include_video_files:
            download_nodes.extend([ContentNode for ContentNode in content_extractor.get_video_file_objects()])

        if include_audio_files:
            download_nodes.extend([ContentNode for ContentNode in content_extractor.get_audio_file_objects()])

        if include_image_files:
            download_nodes.extend([ContentNode for ContentNode in content_extractor.get_image_file_objects()])

        for ContentNode in download_nodes:

            if is_hidden(ContentNode):
                if download_hidden_files:
                    print(f"Including hidden file: {ContentNode.title} {ContentNode.url}\n")
                else:
                    continue

            if ContentNode.url in download_manifest:
                print(f"Skipping {ContentNode.url} because it has already been downloaded.")
                continue

            full_file_path = path_constructor(root_directory,
                                              ContentNode,
                                              flatten)

            self._download_file(ContentNode.url, full_file_path, bool(force_to_shortcut.match(ContentNode.url)))

            download_manifest.append(ContentNode.url)

        write_to_download_manifest(root_directory, "downloaded_files", download_manifest)

    def _download_file(self, url, filename:str, force_to_shortcut=False):

        """
        Downloads a file from a URL to a specified location.
        :param url:
        :param filename:
        :param force_to_shortcut:
        :return:
        """

        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))

        if force_to_shortcut:
            return create_windows_shortcut_from_url(url, filename)

        try:
            response = requests.get(url, stream=True, verify=True, headers=user_agent)

            if response.status_code in [401, 402, 403, 404, 405, 406]:
                log.warning(f"Response Error {response.status_code} {response.reason} {url} {filename}\n")
                print(f"Response Error {response.status_code} {response.reason} {url} {filename}\n")
                return create_windows_shortcut_from_url(url, filename)
            else:
                try:
                    print(f"Downloading {url} to {filename}...\n")
                    with open(filename, 'wb') as file:

                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                file.write(chunk)
                                file.flush()
                                os.fsync(file.fileno())

                    return filename

                except PermissionError as exc:
                    log.exception(f"Permission Error: {exc}, {filename}")
                    print(f"Permission Error: {filename}\n")
                    return create_windows_shortcut_from_url(url, filename)

        except requests.exceptions.ConnectionError as exc:
            log.exception(f"Connection Error: {exc}, {url}")
            print(f"Connection Error: {exc}, {url}\n")
            return create_windows_shortcut_from_url(url, filename)

        except MissingSchema as exc:
            log.exception(f"Missing Schema Error: {exc}, {url}")
            print(f"Missing Schema Error: {exc}, {url}\n")

        except InvalidURL as exc:
            log.exception(f"Invalid URL Error: {exc}, {url}")
            print(f"Invalid URL Error: {exc}, {url}\n")






